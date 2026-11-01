# ruff: noqa: F811  (pytest fixtures are imported by name so this module can use them)
"""Completing a booking writes what each service earned its staff member (S1a), on disposable PostgreSQL."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.infrastructure.db.repositories import staff_earnings_repository
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_payment_ledger_sql import TEST_DB
from tests.integration.test_staff_earnings_sql import (  # noqa: F401
    SafetyEnv,
    a_booking,
    attribute,
    digest,
    env,
    rule,
    staff_db,
)

pytestmark = [pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")]


async def finish(env, f, booking):
    paid = await env.collect(f, {"id": booking}, method="cash")
    assert isinstance(paid, dict), paid
    done = await env.complete(f, {"id": booking})
    assert isinstance(done, dict), done
    return done


async def earnings(env, booking):
    return await env.sql(
        """select staff_id::text as staff, amount_paise, service_value_paise, commission_type, rate_basis_points,
                  fixed_amount_paise, attribution_source, rule_version_id is not null as has_rule
           from staff_earnings where booking_id = :b""",
        b=booking,
    )


async def test_a_completed_service_earns_its_staff_member_the_rule_in_force(env):
    f, booking = await a_booking(env)  # the seeded service costs 250 rupees
    await rule(env, f, bps=2000)
    await finish(env, f, booking)
    assert await earnings(env, booking) == [{
        "staff": f["staff"], "amount_paise": 5_000, "service_value_paise": 25_000,
        "commission_type": "PERCENT_OF_SERVICE_VALUE", "rate_basis_points": 2000, "fixed_amount_paise": None,
        "attribution_source": "booking_staff", "has_rule": True,
    }]


async def test_with_no_rule_the_service_is_still_recorded_and_earns_nothing(env):
    f, booking = await a_booking(env)
    await finish(env, f, booking)
    assert await earnings(env, booking) == [{
        "staff": f["staff"], "amount_paise": 0, "service_value_paise": 25_000, "commission_type": "NONE",
        "rate_basis_points": None, "fixed_amount_paise": None, "attribution_source": "booking_staff", "has_rule": False,
    }]


async def test_the_most_specific_rule_wins(env):
    f, booking = await a_booking(env)
    await rule(env, f, bps=9000)  # salon default
    await rule(env, f, staff=f["staff"], bps=3000)  # staff-wide
    await rule(env, f, staff=f["staff"], service=f["service"], type="FIXED_PER_SERVICE", bps=None, fixed=7_000)
    await finish(env, f, booking)
    row = (await earnings(env, booking))[0]
    assert (row["commission_type"], row["amount_paise"], row["fixed_amount_paise"]) == ("FIXED_PER_SERVICE", 7_000, 7_000)


async def test_a_fixed_amount_above_the_price_is_capped_at_the_price(env):
    f, booking = await a_booking(env)
    await rule(env, f, type="FIXED_PER_SERVICE", bps=None, fixed=99_000)
    await finish(env, f, booking)
    assert (await earnings(env, booking))[0]["amount_paise"] == 25_000


async def test_the_owner_named_staff_member_gets_the_earning_not_the_booking_staff(env):
    f, booking = await a_booking(env)
    other = str(uuid4())
    await env.sql("insert into staff(id, salon_id, name) values(:i, :s, 'Second barber')", i=other, s=f["salon"])
    await attribute(env, f, booking, other, 1)
    await rule(env, f, bps=1000)
    await finish(env, f, booking)
    row = (await earnings(env, booking))[0]
    assert (row["staff"], row["attribution_source"], row["amount_paise"]) == (other, "attributed", 2_500)


async def test_a_rule_made_after_completion_never_changes_the_earning(env):
    f, booking = await a_booking(env)
    await rule(env, f, version=1, bps=2000)
    await finish(env, f, booking)
    await rule(env, f, version=2, bps=9000)
    row = (await earnings(env, booking))[0]
    assert (row["rate_basis_points"], row["amount_paise"]) == (2000, 5_000)


async def test_a_rule_that_starts_later_does_not_apply_to_a_service_completed_before_it(env):
    f, booking = await a_booking(env)
    await env.sql(
        """insert into staff_commission_rule_versions(salon_id, version, commission_type, rate_basis_points,
             effective_from, idempotency_key, request_hash)
           values(:s, 1, 'PERCENT_OF_SERVICE_VALUE', 5000, now() + interval '1 day', :k, :h)""",
        s=f["salon"], k="future-" + uuid4().hex, h=digest("future"),
    )
    await finish(env, f, booking)
    assert (await earnings(env, booking))[0]["amount_paise"] == 0


async def test_another_salons_rules_never_apply(env):
    f, booking = await a_booking(env)
    other = await env.seed()
    await rule(env, other, bps=10_000)
    await finish(env, f, booking)
    assert (await earnings(env, booking))[0]["amount_paise"] == 0


async def test_repeating_the_completion_does_not_earn_twice(env):
    f, booking = await a_booking(env)
    await rule(env, f, bps=2000)
    await finish(env, f, booking)
    async with env.session() as session:
        assert await staff_earnings_repository.record_staff_earnings(session, booking) == 0
        await session.commit()
    assert len(await earnings(env, booking)) == 1


async def test_a_booking_that_is_not_completed_earns_nothing(env):
    _, booking = await a_booking(env)
    async with env.session() as session:
        assert await staff_earnings_repository.record_staff_earnings(session, booking) == 0
    assert await earnings(env, booking) == []


async def test_a_problem_recording_earnings_never_stops_the_service_completing(env, monkeypatch):
    f, booking = await a_booking(env)

    def broken(*args, **kwargs):
        raise RuntimeError("commission bug")

    monkeypatch.setattr(staff_earnings_repository, "select_rule", broken)
    done = await finish(env, f, booking)
    assert done["status"] == "completed"
    assert await earnings(env, booking) == []
    # ...and the earning can be recreated safely once the problem is fixed.
    monkeypatch.undo()
    async with env.session() as session:
        assert await staff_earnings_repository.record_staff_earnings(session, booking) == 1
        await session.commit()
    assert len(await earnings(env, booking)) == 1


async def test_nothing_changes_for_a_salon_before_the_migration_exists(env):
    """record_staff_earnings is a no-op where the tables are missing (the code can ship before the migration)."""
    _, booking = await a_booking(env)
    async with env.session() as session:
        await session.execute(text("alter table staff_earnings rename to staff_earnings_hidden"))
        try:
            assert await staff_earnings_repository.record_staff_earnings(session, booking) == 0
        finally:
            await session.rollback()
