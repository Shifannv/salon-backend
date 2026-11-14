"""Real PostgreSQL: the no-show warning lifecycle (warn, withdraw, customer reply, expiry, read model).

Opt-in through MIGRATION_TEST_DB (a disposable local PostgreSQL admin URL); reuses the seeded
fixture from test_checkout_safety_sql. The unit tests use fakes, so this is the only place the
warning SQL runs against the real schema, triggers and grants.
"""

import pytest

from app.core.exceptions import AppError, ConflictError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import set_actor_context
from tests.integration.test_checkout_safety_sql import safety, safety_db  # noqa: F401  (fixtures)
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


async def _started_confirmed_booking(env, fixture, delta=0):
    booking = await env.book(fixture, delta=delta)
    assert isinstance(booking, dict), booking
    await env.sql(
        "update bookings set start_datetime=now()-interval '20 minutes', "
        "end_datetime=now()+interval '10 minutes' where id=:id",
        id=booking["id"],
    )
    await env.sql("update bookings set status='confirmed' where id=:id", id=booking["id"])
    return booking


async def _as(env, actor, call):
    async with env.session() as session:
        await set_actor_context(session, actor)
        return await call(PlatformRepository(session))


async def test_warn_replays_and_rejects_a_second_open_warning(safety):  # noqa: F811
    f = await safety.seed()
    booking = await _started_confirmed_booking(safety, f)

    warned = await _as(safety, f["owner"], lambda r: r.create_no_show_warning(f["owner"], booking["id"], 10, "warn-key-0001"))
    assert warned["no_show_warning"]["grace_minutes"] == 10
    assert warned["_outbox_ids"]

    replay = await _as(safety, f["owner"], lambda r: r.create_no_show_warning(f["owner"], booking["id"], 10, "warn-key-0001"))
    assert replay["_idempotency_replay"] is True

    with pytest.raises(ConflictError):
        await _as(safety, f["owner"], lambda r: r.create_no_show_warning(f["owner"], booking["id"], 10, None))

    listed = await _as(safety, f["owner"], lambda r: r.list_bookings(f["owner"], "owner"))
    assert any(row["id"] == booking["id"] and row["no_show_warning"] for row in listed)


async def test_warn_without_a_key_then_withdraw(safety):  # noqa: F811
    f = await safety.seed()
    booking = await _started_confirmed_booking(safety, f)

    warned = await _as(safety, f["owner"], lambda r: r.create_no_show_warning(f["owner"], booking["id"], 5, None))
    assert warned["no_show_warning"]["customer_response"] is None

    withdrawn = await _as(safety, f["owner"], lambda r: r.withdraw_no_show_warning(f["owner"], booking["id"]))
    assert withdrawn["no_show_warning"] is None


async def test_customer_reply_on_the_way_then_not_coming_cancels(safety):  # noqa: F811
    f = await safety.seed()
    booking = await _started_confirmed_booking(safety, f)
    await _as(safety, f["owner"], lambda r: r.create_no_show_warning(f["owner"], booking["id"], 15, None))

    replied = await _as(
        safety, f["customer"],
        lambda r: r.respond_to_no_show_warning(f["customer"], booking["id"], "on_the_way", None, None, None),
    )
    assert replied["no_show_warning"]["customer_response"] == "on_the_way"


async def test_expired_warning_marks_the_booking_no_show(safety):  # noqa: F811
    f = await safety.seed()
    booking = await _started_confirmed_booking(safety, f)
    await _as(safety, f["owner"], lambda r: r.create_no_show_warning(f["owner"], booking["id"], 5, None))
    await safety.sql(
        "update booking_no_show_warnings set deadline_at=now()-interval '1 minute', "
        "warned_at=now()-interval '10 minutes' where booking_id=:id",
        id=booking["id"],
    )

    processed = await _as(safety, f["owner"], lambda r: r.expire_no_show_warnings())
    assert processed == 1
    row = (await safety.sql("select status from bookings where id=:id", id=booking["id"]))[0]
    assert row["status"] in {"no_show", "cancelled"}


async def test_warning_on_an_unconfirmed_booking_is_a_conflict_not_a_server_error(safety):  # noqa: F811
    f = await safety.seed()
    booking = await safety.book(f)
    assert isinstance(booking, dict)
    with pytest.raises(AppError):
        await _as(safety, f["owner"], lambda r: r.create_no_show_warning(f["owner"], booking["id"], 10, None))
