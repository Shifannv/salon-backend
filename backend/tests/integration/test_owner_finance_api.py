"""Owner finance cash book API on disposable PostgreSQL: real bookings and payments end to end."""

from datetime import UTC, date, datetime, timedelta, timezone
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
            "title": "Test item", "category": "supplies", "amount_paise": 5000, "payment_method": "cash",
            "occurred_at": iso_now(minutes=1), "note": "towels"})
        assert spent.status_code == 201, spent.text
        assert (await http.post("/v1/salons/me/expenses", headers=key(), json={
            "title": "Test item", "category": "utilities", "amount_paise": 20000, "payment_method": "non_cash",
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
    body = {"title": "Test item", "category": "rent", "amount_paise": 800000, "payment_method": "non_cash",
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
    good = {"title": "Test item", "category": "supplies", "amount_paise": 100, "payment_method": "cash", "occurred_at": iso_now(minutes=1)}
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
                    "title": "Test item", "category": "supplies", "amount_paise": 100, "payment_method": "cash", "occurred_at": iso_now()}),
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
                    "title": "Test item", "category": "supplies", "amount_paise": 100, "payment_method": "cash", "occurred_at": iso_now()}),
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
            "title": "Test item", "category": "rent", "amount_paise": 12345, "payment_method": "non_cash", "occurred_at": iso_now(minutes=1)})
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
            "title": "Test item", "category": "supplies", "amount_paise": 777, "payment_method": "cash", "occurred_at": iso_now(minutes=1)})
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
                      "bank", "token", "secret"):
        assert forbidden not in raw


def at(days_ago=0, **delta):
    return (datetime.now(UTC) - timedelta(days=days_ago, **delta)).isoformat()


def item(client_id=None, **overrides):
    values = {"client_id": client_id or "batch-" + uuid4().hex, "title": "Tea", "category": "supplies",
              "amount_paise": 1500, "payment_method": "cash", "occurred_at": at(minutes=1), "note": None}
    values.update(overrides)
    return values


async def test_a_batch_records_many_expenses_in_one_call_and_a_retry_replays_it(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        items = [item(title="Tea"), item(title="Towels", amount_paise=4000, payment_method="non_cash"),
                 item(title="Soap", category="maintenance")]
        first = await http.post("/v1/salons/me/expenses/batch", json={"items": items})
        assert first.status_code == 200, first.text
        results = first.json()["results"]
        assert [r["status"] for r in results] == ["created"] * 3
        assert [r["client_id"] for r in results] == [i["client_id"] for i in items]
        assert results[1]["expense"]["title"] == "Towels" and results[1]["expense"]["seq"] > results[0]["expense"]["seq"]

        again = await http.post("/v1/salons/me/expenses/batch", json={"items": items})
        assert [r["status"] for r in again.json()["results"]] == ["replayed"] * 3
        assert [r["expense"]["id"] for r in again.json()["results"]] == [r["expense"]["id"] for r in results]
        assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s", s=f["salon"]))[0]["n"] == 3


async def test_one_bad_item_never_blocks_the_others_in_a_batch(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        reused = item()
        assert (await http.post("/v1/salons/me/expenses/batch", json={"items": [reused]})).status_code == 200
        items = [
            item(title="Good one"),
            item(title="From tomorrow", occurred_at=(datetime.now(UTC) + timedelta(days=1)).isoformat()),
            {**reused, "amount_paise": 99999},  # same key, different body
            item(title="Good two"),
        ]
        body = (await http.post("/v1/salons/me/expenses/batch", json={"items": items})).json()["results"]
        assert [r["status"] for r in body] == ["created", "rejected", "rejected", "created"]
        assert body[1]["code"] == "validation_error" and body[1]["expense"] is None
        assert body[2]["code"] == "idempotency_key_reuse"
        assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s", s=f["salon"]))[0]["n"] == 3


async def test_the_same_key_twice_in_one_batch_is_recorded_once(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        same = item()
        body = (await http.post("/v1/salons/me/expenses/batch", json={"items": [same, same]})).json()["results"]
        assert [r["status"] for r in body] == ["created", "replayed"]
        assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s", s=f["salon"]))[0]["n"] == 1


async def test_a_batch_is_bounded_and_strictly_shaped(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        assert (await http.post("/v1/salons/me/expenses/batch", json={"items": [item() for _ in range(50)]})).status_code == 200
        assert (await http.post("/v1/salons/me/expenses/batch", json={"items": [item() for _ in range(51)]})).status_code == 422
        assert (await http.post("/v1/salons/me/expenses/batch", json={"items": []})).status_code == 422
        for bad in ({"title": "   "}, {"title": "x" * 81}, {"amount_paise": 0}, {"amount_paise": 1.5},
                    {"client_id": "short"}, {"category": "bribes"}, {"payment_method": "crypto"},
                    {"surprise": 1}, {"occurred_at": "2026-10-29T10:00:00"}):
            response = await http.post("/v1/salons/me/expenses/batch", json={"items": [item(**bad)]})
            assert response.status_code == 422, (bad, response.text)


async def test_a_batch_is_refused_outright_once_the_plan_has_ended_and_for_non_owners(env, monkeypatch):
    ended = await trial_salon(env, days=-1)
    http, _ = await client_for(env, monkeypatch, make_owner(ended["owner"]))
    async with http:
        response = await http.post("/v1/salons/me/expenses/batch", json={"items": [item()]})
        assert response.status_code == 403 and response.json()["error"]["code"] == "entitlement_required"
        assert (await http.get("/v1/salons/me/expenses/changes", params={"after": 0})).status_code == 200
        assert (await http.get("/v1/salons/me/expenses/summary", params={"month": today().strftime("%Y-%m")})).status_code == 200
    assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s", s=ended["salon"]))[0]["n"] == 0

    live = await trial_salon(env)
    customer = Profile(id=live["customer"], role=Role.customer, full_name="C", email="c@example.test",
                       phone=None, phone_verified=False, avatar_url=None, is_active=True)
    http, _ = await client_for(env, monkeypatch, customer)
    async with http:
        for response in (await http.post("/v1/salons/me/expenses/batch", json={"items": [item()]}),
                         await http.get("/v1/salons/me/expenses/changes", params={"after": 0}),
                         await http.get("/v1/salons/me/expenses/summary", params={"month": "2026-10"})):
            assert response.status_code == 403


async def test_the_change_feed_pages_in_order_and_includes_cancellations(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        made = (await http.post("/v1/salons/me/expenses/batch", json={"items": [item(title=f"E{n}") for n in range(5)]})).json()["results"]
        victim = made[1]["expense"]["id"]
        assert (await http.post(f"/v1/salons/me/expenses/{victim}/reverse", headers=key())).status_code == 201

        page = (await http.get("/v1/salons/me/expenses/changes", params={"after": 0, "limit": 4})).json()
        assert len(page["expenses"]) == 4 and page["has_more"] is True
        seqs = [row["seq"] for row in page["expenses"]]
        assert seqs == sorted(seqs) and page["next_cursor"] == seqs[-1]

        rest = (await http.get("/v1/salons/me/expenses/changes", params={"after": page["next_cursor"], "limit": 4})).json()
        assert [row["entry_type"] for row in rest["expenses"]] == ["expense", "reversal"] and rest["has_more"] is False
        reversal = rest["expenses"][-1]
        assert reversal["reverses_id"] == victim and reversal["title"] == "E1"

        caught_up = (await http.get("/v1/salons/me/expenses/changes", params={"after": rest["next_cursor"]})).json()
        assert caught_up["expenses"] == [] and caught_up["next_cursor"] == rest["next_cursor"] and caught_up["has_more"] is False
        assert (await http.get("/v1/salons/me/expenses/changes", params={"after": -1})).status_code == 422
        assert (await http.get("/v1/salons/me/expenses/changes", params={"after": 0, "limit": 501})).status_code == 422


async def test_the_change_feed_only_ever_shows_the_callers_own_salon(env, monkeypatch):
    mine, theirs = await trial_salon(env), await trial_salon(env)
    http, identity = await client_for(env, monkeypatch, make_owner(theirs["owner"]))
    async with http:
        await http.post("/v1/salons/me/expenses/batch", json={"items": [item(title="Secret")]})
        identity["actor"] = make_owner(mine["owner"])
        feed = (await http.get("/v1/salons/me/expenses/changes", params={"after": 0})).json()
        assert feed["expenses"] == []
        month = today().strftime("%Y-%m")
        summary = (await http.get("/v1/salons/me/expenses/summary", params={"month": month})).json()
        assert summary["days"] == [] and summary["totals"]["total_paise"] == 0


async def test_cancelling_an_old_expense_changes_that_day_and_never_today(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    day = (today() - timedelta(days=1)).isoformat()
    async with http:
        made = (await http.post("/v1/salons/me/expenses/batch", json={"items": [
            item(title="Petrol", amount_paise=30000, occurred_at=at(days_ago=1))]})).json()["results"][0]["expense"]
        before_today = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()

        assert (await http.post(f"/v1/salons/me/expenses/{made['id']}/reverse", headers=key())).status_code == 201

        after_today = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
        assert after_today["expenses_total_paise"] == before_today["expenses_total_paise"] == 0
        assert after_today["expected_closing_cash_paise"] == before_today["expected_closing_cash_paise"]
        old = (await http.get("/v1/salons/me/ledger/daily", params={"date": day})).json()
        assert old["expenses"] == {"cash_paise": 0, "non_cash_paise": 0}  # the cancellation netted out on its own day
        listing = (await http.get("/v1/salons/me/expenses", params={"from": day, "to": day})).json()["expenses"]
        assert {row["occurred_at"] for row in listing if row["id"] == made["id"] or row["reverses_id"] == made["id"]} \
            == {made["occurred_at"]}


async def test_the_month_summary_is_the_servers_own_total_per_day_and_matches_the_ledger(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        batch = [item(title="Tea", amount_paise=1500, payment_method="cash", occurred_at=at(minutes=2)),
                 item(title="Power", amount_paise=20000, payment_method="non_cash", occurred_at=at(minutes=3)),
                 item(title="Soap", amount_paise=700, payment_method="cash", occurred_at=at(minutes=4))]
        results = (await http.post("/v1/salons/me/expenses/batch", json={"items": batch})).json()["results"]
        soap = results[2]["expense"]["id"]
        assert (await http.post(f"/v1/salons/me/expenses/{soap}/reverse", headers=key())).status_code == 201

        month = today().strftime("%Y-%m")
        summary = (await http.get("/v1/salons/me/expenses/summary", params={"month": month})).json()
        assert summary["month"] == month and summary["timezone"] == "Asia/Kolkata"
        todays = next(day for day in summary["days"] if day["date"] == today().isoformat())
        assert todays == {"date": today().isoformat(), "cash_paise": 1500, "non_cash_paise": 20000,
                          "total_paise": 21500, "count": 2}
        assert summary["totals"] == {"cash_paise": 1500, "non_cash_paise": 20000, "total_paise": 21500, "count": 2}

        ledger = (await http.get("/v1/salons/me/ledger/daily", params={"date": today().isoformat()})).json()
        assert ledger["expenses"] == {"cash_paise": todays["cash_paise"], "non_cash_paise": todays["non_cash_paise"]}
        assert ledger["expenses_total_paise"] == todays["total_paise"]  # one source, two views

        empty = (await http.get("/v1/salons/me/expenses/summary", params={"month": "2020-01"})).json()
        assert empty["days"] == [] and empty["totals"] == {"cash_paise": 0, "non_cash_paise": 0, "total_paise": 0, "count": 0}
        for bad in ("", "2026", "2026-13", "2026-10-01", "oct-2026"):
            assert (await http.get("/v1/salons/me/expenses/summary", params={"month": bad})).status_code == 422


async def test_a_day_that_was_closed_says_so_when_its_figures_change_afterwards(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        day = (today() - timedelta(days=1)).isoformat()
        closed = await http.post(f"/v1/salons/me/ledger/days/{day}/close", headers=key(),
                                 json={"actual_cash_paise": 0, "opening_cash_paise": 0})
        assert closed.status_code == 200 and closed.json()["close"]["changed_since_close"] is False

        await http.post("/v1/salons/me/expenses/batch", json={"items": [
            item(title="Forgot to enter", amount_paise=5000, occurred_at=at(days_ago=1))]})
        ledger = (await http.get("/v1/salons/me/ledger/daily", params={"date": day})).json()
        assert ledger["close"]["changed_since_close"] is True
        assert ledger["close"]["expected_cash_paise"] == 0  # the stored count is never rewritten
        assert ledger["expected_closing_cash_paise"] == -5000


async def test_the_cursor_has_an_upper_bound_so_a_huge_value_is_a_422_not_a_500(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        assert (await http.get("/v1/salons/me/expenses/changes", params={"after": 2**63 - 1})).status_code == 200
        assert (await http.get("/v1/salons/me/expenses/changes", params={"after": 2**63})).status_code == 422


async def test_the_same_instant_written_in_another_zone_is_the_same_request_when_retried(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    moment = datetime.now(UTC) - timedelta(minutes=5)
    india = moment.astimezone(timezone(timedelta(hours=5, minutes=30)))
    async with http:
        first = item(occurred_at=moment.isoformat())
        again = {**first, "occurred_at": india.isoformat()}
        one = (await http.post("/v1/salons/me/expenses/batch", json={"items": [first]})).json()["results"][0]
        two = (await http.post("/v1/salons/me/expenses/batch", json={"items": [again]})).json()["results"][0]
        assert (one["status"], two["status"]) == ("created", "replayed")


async def test_a_database_timeout_is_not_reported_as_a_refused_expense(env, monkeypatch):
    """Only a real constraint failure is 'rejected'. A lock timeout must surface as an error the
    phone retries, never as a verdict that makes it discard a valid expense."""
    from sqlalchemy.exc import OperationalError

    from app.infrastructure.db.repositories.finance_repository import FinanceRepository

    f = await trial_salon(env)

    async def times_out(self, values):
        class Orig(Exception):
            sqlstate = "55P03"  # lock_not_available

        raise OperationalError("insert", {}, Orig("lock timeout"))

    monkeypatch.setattr(FinanceRepository, "add_expense", times_out)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    http._transport.raise_app_exceptions = False
    async with http:
        response = await http.post("/v1/salons/me/expenses/batch", json={"items": [item()]})
        assert response.status_code >= 500

