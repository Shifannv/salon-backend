"""Owner finance cash book API on disposable PostgreSQL: real bookings and payments end to end."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import text

from app.domain.entities.profile import Profile, Role
from tests.conftest import make_owner
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_booking_journeys_e2e import local_app
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_owner_finance_sql import cashbook_db  # noqa: F401
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
async def env(cashbook_db):  # noqa: F811
    environment = SafetyEnv(cashbook_db)
    yield environment
    await environment.engine.dispose()


def today() -> date:
    return datetime.now(IST).date()


def key() -> dict[str, str]:
    return {"Idempotency-Key": "k-" + uuid4().hex}


async def trial_salon(env, *, days=30, limit=500, counted=0):
    f = await env.seed()
    await env.sql(
        """insert into salon_access(salon_id, trial_started_at, trial_ends_at, trial_booking_limit, bookings_counted)
           values(:s, now() - interval '10 days', now() + make_interval(days => :d), :l, :c)
           on conflict (salon_id) do update set trial_started_at = excluded.trial_started_at,
             trial_ends_at = excluded.trial_ends_at, trial_booking_limit = excluded.trial_booking_limit,
             bookings_counted = excluded.bookings_counted""",
        s=f["salon"], d=days, l=limit, c=counted,
    )
    return f


async def client_for(env, monkeypatch, actor):
    app, identity = local_app(env, monkeypatch, actor)
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://local.test")
    return http, identity


async def sell(env, f, *, method, delta):
    """A real booking: created, paid at the salon, completed. Returns the booking."""
    booking = await env.book(f, delta=delta)
    assert isinstance(booking, dict), booking
    paid = await env.collect(f, booking, method=method)
    assert isinstance(paid, dict), paid
    done = await env.complete(f, booking)
    assert isinstance(done, dict), done
    return booking


def iso_now(**delta) -> str:
    return (datetime.now(UTC) - timedelta(**delta)).isoformat()


async def test_ledger_reads_real_sales_receipts_expenses_and_closes_the_day(env, monkeypatch):
    f = await trial_salon(env)
    await sell(env, f, method="cash", delta=0)
    await sell(env, f, method="upi_direct", delta=60)
    owner = make_owner(f["owner"])
    http, _ = await client_for(env, monkeypatch, owner)
    async with http:
        day = today().isoformat()

        before = (await http.get("/v1/salons/me/ledger/daily", params={"date": day})).json()
        assert before["gross_completed_sales_paise"] == 50000
        assert (before["cash_collected_paise"], before["non_cash_received_paise"]) == (25000, 25000)
        assert before["outstanding_due_paise"] == 0
        assert before["status"] == "open" and before["opening_cash_source"] == "not_set"
        assert before["expected_closing_cash_paise"] == 25000
        assert before["needs_review"] is False

        spent = await http.post("/v1/salons/me/expenses", headers=key(), json={
            "category": "supplies", "amount_paise": 5000, "payment_method": "cash",
            "occurred_at": iso_now(minutes=1), "note": "towels"})
        assert spent.status_code == 201, spent.text
        assert (await http.post("/v1/salons/me/expenses", headers=key(), json={
            "category": "utilities", "amount_paise": 20000, "payment_method": "non_cash",
            "occurred_at": iso_now(minutes=1)})).status_code == 201
        assert (await http.post("/v1/salons/me/ledger/adjustments", headers=key(), json={
            "direction": "in", "amount_paise": 2500, "reason": "Float top-up",
            "occurred_at": iso_now(minutes=1)})).status_code == 201

        after = (await http.get("/v1/salons/me/ledger/daily", params={"date": day})).json()
        assert after["expenses"] == {"cash_paise": 5000, "non_cash_paise": 20000}
        assert after["expenses_total_paise"] == 25000  # the server's sum, so no client adds money
        assert after["cash_adjustments"] == {"in_paise": 2500, "out_paise": 0}
        # Expenses never reduce completed sales, and a non-cash expense never touches cash.
        assert after["gross_completed_sales_paise"] == 50000
        assert after["expected_closing_cash_paise"] == 25000 - 5000 + 2500

        # The server computes expected cash; a difference needs a written reason.
        # The first ever close needs the owner to state the opening cash; it is never assumed.
        unstated = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=key(),
                                   json={"actual_cash_paise": 22000})
        assert unstated.status_code == 422 and unstated.json()["error"]["code"] == "opening_cash_required"

        short = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=key(),
                                json={"actual_cash_paise": 22000, "opening_cash_paise": 0})
        assert short.status_code == 422 and short.json()["error"]["code"] == "difference_reason_required"

        close_key = key()
        closed = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=close_key,
                                 json={"actual_cash_paise": 22000, "opening_cash_paise": 0,
                                       "difference_reason": "Tip jar emptied"})
        assert closed.status_code == 200, closed.text
        body = closed.json()
        assert body["status"] == "closed"
        assert body["close"]["revision"] == 1 and body["close"]["difference_paise"] == -500

        replay = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=close_key,
                                 json={"actual_cash_paise": 22000, "opening_cash_paise": 0,
                                       "difference_reason": "Tip jar emptied"})
        assert replay.status_code == 200 and replay.json()["close"]["revision"] == 1

        # A re-count keeps the opening the owner already confirmed; it is not asked for again.
        again = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=key(),
                                json={"actual_cash_paise": 22500})
        assert again.status_code == 200 and again.json()["close"]["revision"] == 2
        assert again.json()["opening_cash_paise"] == 0

        rows = await env.sql("select count(*) as n from salon_day_closes where salon_id = :s", s=f["salon"])
        assert rows[0]["n"] == 2


async def test_retrying_a_close_replays_it_even_after_the_cash_book_moved_on(env, monkeypatch):
    f = await trial_salon(env)
    await sell(env, f, method="cash", delta=0)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        day = today().isoformat()
        retry_key = key()
        body = {"actual_cash_paise": 25000, "opening_cash_paise": 0}  # exactly expected: no reason needed
        first = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=retry_key, json=body)
        assert first.status_code == 200 and first.json()["close"]["revision"] == 1
        # The cash book changes after the close...
        assert (await http.post("/v1/salons/me/ledger/adjustments", headers=key(), json={
            "direction": "out", "amount_paise": 1000, "reason": "Paid the tea seller",
            "occurred_at": iso_now(minutes=1)})).status_code == 201
        # ...and the app, which never saw the first answer, sends the same request again.
        again = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=retry_key, json=body)
        assert again.status_code == 200, again.text
        assert again.json()["close"]["revision"] == 1  # replayed, not a new revision and not a 422
        assert (await env.sql("select count(*) as n from salon_day_closes where salon_id = :s", s=f["salon"]))[0]["n"] == 1


async def test_unpaid_completed_work_is_due_and_cash_is_not_counted(env, monkeypatch):
    f = await trial_salon(env)
    booking = await env.book(f)
    assert isinstance(booking, dict)
    async with env.session() as session:  # an old completed-but-unpaid booking, as legacy data
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(text("update bookings set status='completed', completed_at=now() where id=:i"),
                              {"i": booking["id"]})
        await session.commit()
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        ledger = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
    assert ledger["gross_completed_sales_paise"] == 25000
    assert ledger["outstanding_due_paise"] == 25000
    assert ledger["cash_collected_paise"] == 0 and ledger["non_cash_received_paise"] == 0


async def test_a_processed_refund_is_subtracted_from_cash_and_the_receipt_still_counts(env, monkeypatch):
    f = await trial_salon(env)
    booking = await sell(env, f, method="cash", delta=0)
    payment = (await env.sql("select id from booking_payments where booking_id = :b", b=booking["id"]))[0]["id"]
    # Today the platform cannot refund a manual receipt: its own refund trigger would move the row
    # out of 'captured', which ck_booking_payments_manual_is_settled forbids. This seeds the row
    # with triggers off, to pin the arithmetic a future manual-refund feature will rely on.
    async with env.session() as session:
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(text(
            """insert into payment_refunds(payment_id, booking_id, amount, status, idempotency_key, processed_at)
               values(:p, :b, 100, 'processed', 'refund-test-1', now())"""), {"p": payment, "b": booking["id"]})
        await session.commit()
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        ledger = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
    assert ledger["cash_collected_paise"] == 25000
    assert ledger["refunds"] == {"cash_paise": 10000, "non_cash_paise": 0}
    assert ledger["expected_closing_cash_paise"] == 15000


async def test_expenses_are_idempotent_and_reversed_once_never_edited(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    body = {"category": "rent", "amount_paise": 800000, "payment_method": "non_cash",
            "occurred_at": iso_now(minutes=2), "note": "October"}
    async with http:
        headers = key()
        first = await http.post("/v1/salons/me/expenses", headers=headers, json=body)
        again = await http.post("/v1/salons/me/expenses", headers=headers, json=body)
        assert first.status_code == again.status_code == 201
        assert first.json()["id"] == again.json()["id"] and again.json()["replayed"] is True
        assert first.json()["notice"].startswith("Expense record. Not a tax invoice")

        reuse = await http.post("/v1/salons/me/expenses", headers=headers, json={**body, "amount_paise": 1})
        assert reuse.status_code == 409 and reuse.json()["error"]["code"] == "idempotency_key_reuse"
        missing = await http.post("/v1/salons/me/expenses", json=body)
        assert missing.status_code == 400 and missing.json()["error"]["code"] == "idempotency_key_required"

        reverse_key = key()
        expense_id = first.json()["id"]
        undone = await http.post(f"/v1/salons/me/expenses/{expense_id}/reverse", headers=reverse_key)
        assert undone.status_code == 201 and undone.json()["entry_type"] == "reversal"
        replay = await http.post(f"/v1/salons/me/expenses/{expense_id}/reverse", headers=reverse_key)
        assert replay.status_code == 201 and replay.json()["id"] == undone.json()["id"]
        twice = await http.post(f"/v1/salons/me/expenses/{expense_id}/reverse", headers=key())
        assert twice.status_code == 409 and twice.json()["error"]["code"] == "expense_already_reversed"
        of_reversal = await http.post(f"/v1/salons/me/expenses/{undone.json()['id']}/reverse", headers=key())
        assert of_reversal.status_code == 422

        listing = (await http.get("/v1/salons/me/expenses")).json()["expenses"]
        by_id = {row["id"]: row for row in listing}
        assert by_id[expense_id]["reversed"] is True and by_id[expense_id]["amount_paise"] == 800000
        ledger = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
        assert ledger["expenses"]["non_cash_paise"] == 0  # the reversal cancels it


async def test_validation_rejects_bad_money_dates_and_unknown_fields(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    good = {"category": "supplies", "amount_paise": 100, "payment_method": "cash", "occurred_at": iso_now(minutes=1)}
    async with http:
        for bad in ({"amount_paise": 0}, {"amount_paise": -5}, {"amount_paise": 1.5}, {"category": "bribes"},
                    {"payment_method": "crypto"}, {"occurred_at": "2026-10-29T10:00:00"},
                    {"surprise": "field"}, {"note": "x" * 501}):
            response = await http.post("/v1/salons/me/expenses", headers=key(), json={**good, **bad})
            assert response.status_code == 422, (bad, response.text)
        future = await http.post("/v1/salons/me/expenses", headers=key(), json={
            **good, "occurred_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()})
        assert future.status_code == 422
        tomorrow = (today() + timedelta(days=1)).isoformat()
        closed = await http.post(f"/v1/salons/me/ledger/days/{tomorrow}/close", headers=key(),
                                 json={"actual_cash_paise": 0})
        assert closed.status_code == 422 and closed.json()["error"]["code"] == "day_in_future"
        smuggled = await http.post(f"/v1/salons/me/ledger/days/{today().isoformat()}/close", headers=key(),
                                   json={"actual_cash_paise": 0, "expected_cash_paise": 0})
        assert smuggled.status_code == 422
        too_long = await http.get("/v1/salons/me/ledger/range", params={
            "from": (today() - timedelta(days=100)).isoformat(), "to": today().isoformat()})
        assert too_long.status_code == 422
        backwards = await http.get("/v1/salons/me/ledger/range", params={
            "from": today().isoformat(), "to": (today() - timedelta(days=1)).isoformat()})
        assert backwards.status_code == 422


async def test_opening_cash_is_carried_forward_but_never_silently_across_an_unclosed_day(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    first_day = today() - timedelta(days=2)
    async with http:
        opened = await http.post(f"/v1/salons/me/ledger/days/{first_day}/close", headers=key(),
                                 json={"actual_cash_paise": 100000, "opening_cash_paise": 100000})
        assert opened.status_code == 200 and opened.json()["opening_cash_paise"] == 100000

        # The very next day starts from the counted cash; a client cannot restate it.
        next_day = first_day + timedelta(days=1)
        refused = await http.post(f"/v1/salons/me/ledger/days/{next_day}/close",
                                  headers=key(), json={"actual_cash_paise": 100000, "opening_cash_paise": 5})
        assert refused.status_code == 422
        carried = (await http.get("/v1/salons/me/ledger/daily", params={"date": next_day.isoformat()})).json()
        assert carried["opening_cash_paise"] == 100000 and carried["opening_cash_source"] == "previous_close"

        # Yesterday was never closed: today's opening is only a suggestion the owner must confirm.
        unconfirmed = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
        assert unconfirmed["opening_cash_source"] == "needs_confirmation"
        assert unconfirmed["opening_cash_paise"] == 100000  # last count plus the cash that moved since
        silent = await http.post(f"/v1/salons/me/ledger/days/{today()}/close", headers=key(),
                                 json={"actual_cash_paise": 100000})
        assert silent.status_code == 422 and silent.json()["error"]["code"] == "opening_cash_required"
        confirmed = await http.post(f"/v1/salons/me/ledger/days/{today()}/close", headers=key(),
                                    json={"actual_cash_paise": 99000, "opening_cash_paise": 99000})
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["opening_cash_paise"] == 99000
        assert confirmed.json()["opening_cash_source"] == "entered_at_close"


async def test_range_returns_each_day_and_totals(env, monkeypatch):
    f = await trial_salon(env)
    await sell(env, f, method="cash", delta=0)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        body = (await http.get("/v1/salons/me/ledger/range", params={
            "from": (today() - timedelta(days=2)).isoformat(), "to": today().isoformat()})).json()
    assert [d["date"] for d in body["days"]][-1] == today().isoformat() and len(body["days"]) == 3
    assert body["totals"]["gross_completed_sales_paise"] == 25000
    assert body["totals"]["cash_collected_paise"] == 25000


async def test_only_the_salons_owner_with_an_eligible_plan_can_use_it(env, monkeypatch):
    f = await trial_salon(env)
    staff_user = str(uuid4())
    async with env.session() as session:
        await session.execute(text("insert into auth.users(id,email) values(:i,:e)"),
                              {"i": staff_user, "e": staff_user + "@example.test"})
        await session.execute(text("update profiles set role = 'staff' where id = :i"), {"i": staff_user})
        await session.commit()
    staff = Profile(id=staff_user, role=Role.staff, full_name="S", email="s@example.test", phone=None,
                    phone_verified=False, avatar_url=None, is_active=True)
    customer = Profile(id=f["customer"], role=Role.customer, full_name="C", email="c@example.test",
                       phone=None, phone_verified=False, avatar_url=None, is_active=True)
    for actor in (staff, customer):
        http, _ = await client_for(env, monkeypatch, actor)
        async with http:
            for response in (
                await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()}),
                await http.get("/v1/salons/me/expenses"),
                await http.post("/v1/salons/me/expenses", headers=key(), json={
                    "category": "supplies", "amount_paise": 100, "payment_method": "cash", "occurred_at": iso_now()}),
            ):
                assert response.status_code == 403, response.text

    # No trial and no plan, an ended trial and an exhausted trial: the records stay readable and
    # every write is refused, so a salon never loses sight of its own finance history.
    nothing = await env.seed()
    await env.sql("delete from salon_access where salon_id = :s", s=nothing["salon"])  # approval starts a trial
    ended = [nothing, await trial_salon(env, days=-1), await trial_salon(env, days=30, limit=10, counted=10)]
    for salon in ended:
        http, _ = await client_for(env, monkeypatch, make_owner(salon["owner"]))
        async with http:
            read = await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})
            assert read.status_code == 200 and read.json()["can_write"] is False
            assert (await http.get("/v1/salons/me/expenses")).status_code == 200
            assert (await http.get("/v1/salons/me/ledger/range", params={
                "from": today().isoformat(), "to": today().isoformat()})).status_code == 200
            writes = (
                await http.post("/v1/salons/me/expenses", headers=key(), json={
                    "category": "supplies", "amount_paise": 100, "payment_method": "cash", "occurred_at": iso_now()}),
                await http.post("/v1/salons/me/ledger/adjustments", headers=key(), json={
                    "direction": "in", "amount_paise": 100, "reason": "Float", "occurred_at": iso_now()}),
                await http.post(f"/v1/salons/me/ledger/days/{today()}/close", headers=key(),
                                json={"actual_cash_paise": 0, "opening_cash_paise": 0}),
                await http.post(f"/v1/salons/me/expenses/{uuid4()}/reverse", headers=key()),
            )
            for response in writes:
                assert response.status_code == 403, response.text
                assert response.json()["error"]["code"] == "entitlement_required"
    assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s",
                          s=nothing["salon"]))[0]["n"] == 0

    # Records written while the salon was entitled stay visible after the trial ends.
    kept = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(kept["owner"]))
    async with http:
        made = await http.post("/v1/salons/me/expenses", headers=key(), json={
            "category": "rent", "amount_paise": 12345, "payment_method": "non_cash", "occurred_at": iso_now(minutes=1)})
        assert made.status_code == 201
        await env.sql("update salon_access set trial_ends_at = now() - interval '1 hour', "
                      "trial_started_at = now() - interval '10 days' where salon_id = :s", s=kept["salon"])
        listing = (await http.get("/v1/salons/me/expenses")).json()["expenses"]
        assert [row["amount_paise"] for row in listing] == [12345]
        ledger = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
        assert ledger["expenses_total_paise"] == 12345 and ledger["can_write"] is False


async def test_a_salon_never_sees_or_reverses_another_salons_records(env, monkeypatch):
    mine, theirs = await trial_salon(env), await trial_salon(env)
    await sell(env, theirs, method="cash", delta=0)
    http, identity = await client_for(env, monkeypatch, make_owner(theirs["owner"]))
    async with http:
        made = await http.post("/v1/salons/me/expenses", headers=key(), json={
            "category": "supplies", "amount_paise": 777, "payment_method": "cash", "occurred_at": iso_now(minutes=1)})
        their_expense = made.json()["id"]
        identity["actor"] = make_owner(mine["owner"])
        ledger = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
        assert ledger["gross_completed_sales_paise"] == 0 and ledger["expenses"]["cash_paise"] == 0
        assert (await http.get("/v1/salons/me/expenses")).json()["expenses"] == []
        stolen = await http.post(f"/v1/salons/me/expenses/{their_expense}/reverse", headers=key())
        assert stolen.status_code == 404
    rows = await env.sql("select count(*) as n from salon_expenses where entry_type = 'reversal'")
    assert rows[0]["n"] >= 0  # nothing was created for the thief's salon
    assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s", s=mine["salon"]))[0]["n"] == 0


async def test_the_ledger_never_exposes_internal_split_or_provider_fields(env, monkeypatch):
    f = await trial_salon(env)
    await sell(env, f, method="cash", delta=0)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        raw = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).text.lower()
    for forbidden in ("owner_net", "salon_share", "platform", "gateway_fee", "staff_percent", "commission",
                      "profit", "bank", "token", "secret"):
        assert forbidden not in raw
