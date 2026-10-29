"""Auto-repeat expense rules on disposable PostgreSQL: API, tenant isolation, plan gate and the SQL guard."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.domain.entities.profile import Profile, Role
from tests.conftest import make_owner
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_owner_finance_api import client_for, key, trial_salon
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


def rule(**overrides):
    values = {"title": "Shop rent", "category": "rent", "amount_paise": 1500000, "payment_method": "non_cash",
              "note": None, "frequency": "monthly", "start_date": today().isoformat()}
    values.update(overrides)
    return values


async def test_an_owner_creates_lists_and_stops_a_repeating_expense(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        created = await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule(title="  Tea every day ", frequency="daily"))
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["title"] == "Tea every day" and body["active"] is True and body["stopped_at"] is None

        listed = (await http.get("/v1/salons/me/expense-rules")).json()
        assert [r["id"] for r in listed["rules"]] == [body["id"]] and listed["can_write"] is True

        stopped = await http.post(f"/v1/salons/me/expense-rules/{body['id']}/stop")
        assert stopped.status_code == 200 and stopped.json()["active"] is False and stopped.json()["stopped_at"]
        again = await http.post(f"/v1/salons/me/expense-rules/{body['id']}/stop")
        assert again.status_code == 200 and again.json()["stopped_at"] == stopped.json()["stopped_at"]


async def test_a_retried_create_replays_and_a_different_body_with_the_same_key_is_refused(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        headers = key()
        first = await http.post("/v1/salons/me/expense-rules", headers=headers, json=rule())
        second = await http.post("/v1/salons/me/expense-rules", headers=headers, json=rule())
        assert first.status_code == 201 and second.status_code in (200, 201)
        assert second.json()["id"] == first.json()["id"] and second.json()["replayed"] is True
        different = await http.post("/v1/salons/me/expense-rules", headers=headers, json=rule(amount_paise=1))
        assert different.status_code == 409
        assert (await env.sql("select count(*) as n from salon_expense_rules where salon_id = :s", s=f["salon"]))[0]["n"] == 1


@pytest.mark.parametrize("bad", [
    {"amount_paise": 0}, {"title": "   "}, {"frequency": "yearly"}, {"category": "tax"}, {"unknown": 1},
    {"start_date": (today() - timedelta(days=40)).isoformat()},
    {"start_date": (today() + timedelta(days=400)).isoformat()},
])
async def test_an_invalid_rule_is_refused(env, monkeypatch, bad):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        response = await http.post("/v1/salons/me/expense-rules", headers=key(), json={**rule(), **bad})
        assert response.status_code == 422, response.text
    assert (await env.sql("select count(*) as n from salon_expense_rules where salon_id = :s", s=f["salon"]))[0]["n"] == 0


async def test_a_rule_may_start_in_the_future_or_up_to_a_month_back(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        for offset in (-30, 0, 120):
            ok = await http.post("/v1/salons/me/expense-rules", headers=key(),
                                 json=rule(start_date=(today() + timedelta(days=offset)).isoformat()))
            assert ok.status_code == 201, (offset, ok.text)


async def test_at_most_thirty_rules_can_be_active_and_a_retry_is_not_refused_for_it(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        last_key = None
        for i in range(30):
            last_key = key()
            assert (await http.post("/v1/salons/me/expense-rules", headers=last_key, json=rule(title=f"Rule {i}"))).status_code == 201
        over = await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule(title="One too many"))
        assert over.status_code == 422
        retry = await http.post("/v1/salons/me/expense-rules", headers=last_key, json=rule(title="Rule 29"))
        assert retry.status_code in (200, 201) and retry.json()["replayed"] is True
        # Stopping one frees a place.
        first = (await http.get("/v1/salons/me/expense-rules")).json()["rules"][0]["id"]
        assert (await http.post(f"/v1/salons/me/expense-rules/{first}/stop")).status_code == 200
        assert (await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule(title="Now fits"))).status_code == 201


async def test_one_salon_cannot_see_or_stop_anothers_rule(env, monkeypatch):
    mine = await trial_salon(env)
    theirs = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(theirs["owner"]))
    async with http:
        created = await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule())
        rule_id = created.json()["id"]
    http, _ = await client_for(env, monkeypatch, make_owner(mine["owner"]))
    async with http:
        assert (await http.get("/v1/salons/me/expense-rules")).json()["rules"] == []
        assert (await http.post(f"/v1/salons/me/expense-rules/{rule_id}/stop")).status_code == 404
    assert (await env.sql("select active from salon_expense_rules where id = :i", i=rule_id))[0]["active"] is True


async def test_only_the_owner_can_use_rules(env, monkeypatch):
    f = await trial_salon(env)
    customer = Profile(id=f["customer"], role=Role.customer, full_name="C", email="c@example.test",
                       phone=None, phone_verified=False, avatar_url=None, is_active=True)
    http, _ = await client_for(env, monkeypatch, customer)
    async with http:
        assert (await http.get("/v1/salons/me/expense-rules")).status_code == 403
        assert (await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule())).status_code == 403


async def test_after_the_plan_ends_rules_stay_readable_but_cannot_be_created_or_stopped(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        rule_id = (await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule())).json()["id"]
    await env.sql("update salon_access set trial_ends_at = now() - interval '1 day' where salon_id = :s", s=f["salon"])
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        listed = (await http.get("/v1/salons/me/expense-rules")).json()
        assert [r["id"] for r in listed["rules"]] == [rule_id] and listed["can_write"] is False
        assert (await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule())).status_code == 403
        assert (await http.post(f"/v1/salons/me/expense-rules/{rule_id}/stop")).status_code == 403


async def test_an_occurrence_recorded_by_client_id_replays_and_a_cancelled_one_stays_cancelled(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        created = (await http.post("/v1/salons/me/expense-rules", headers=key(), json=rule(frequency="daily"))).json()
        client_id = f"rule:{created['id']}:{today().isoformat()}"
        midnight = datetime.combine(today(), datetime.min.time(), tzinfo=IST).isoformat()
        item = {"client_id": client_id, "title": created["title"], "category": created["category"],
                "amount_paise": created["amount_paise"], "payment_method": created["payment_method"],
                "occurred_at": midnight, "note": None}
        first = (await http.post("/v1/salons/me/expenses/batch", json={"items": [item]})).json()["results"][0]
        again = (await http.post("/v1/salons/me/expenses/batch", json={"items": [item]})).json()["results"][0]
        assert (first["status"], again["status"]) == ("created", "replayed")
        assert first["expense"]["id"] == again["expense"]["id"]

        assert (await http.post(f"/v1/salons/me/expenses/{first['expense']['id']}/reverse", headers=key())).status_code == 201
        after = (await http.post("/v1/salons/me/expenses/batch", json={"items": [item]})).json()["results"][0]
        assert after["status"] == "replayed" and after["expense"]["reversed"] is True  # not brought back
        n = (await env.sql("select count(*) as n from salon_expenses where salon_id = :s and entry_type = 'expense'", s=f["salon"]))[0]["n"]
        assert n == 1


class TestRuleTable:
    async def insert(self, env, salon, **over):
        values = {"salon": salon, "k": "rule-" + uuid4().hex, "title": "Rent", "freq": "monthly"}
        values.update(over)
        rows = await env.sql(
            """insert into salon_expense_rules(salon_id, title, category, amount_paise, payment_method, frequency,
                 start_date, idempotency_key, request_hash)
               values(:salon, :title, 'rent', 1000, 'cash', :freq, current_date, :k, repeat('a', 64)) returning id""",
            **values)
        return str(rows[0]["id"])

    async def refused(self, awaitable, fragment=""):
        with pytest.raises((DBAPIError, IntegrityError)) as caught:
            await awaitable
        assert fragment in str(caught.value), str(caught.value)[:300]

    async def test_a_rule_is_never_edited_only_stopped_once(self, env):
        f = await env.seed()
        rid = await self.insert(env, f["salon"])
        for statement in ("update salon_expense_rules set amount_paise = 1 where id = :i",
                          "update salon_expense_rules set title = 'x' where id = :i",
                          "update salon_expense_rules set frequency = 'daily' where id = :i"):
            await self.refused(env.sql(statement, i=rid), "expense_rule_is_immutable")
        await env.sql("update salon_expense_rules set active = false, stopped_at = now() where id = :i", i=rid)
        await self.refused(env.sql("update salon_expense_rules set active = true, stopped_at = null where id = :i", i=rid),
                           "expense_rule_is_immutable")

    async def test_active_and_stopped_at_must_agree(self, env):
        f = await env.seed()
        rid = await self.insert(env, f["salon"])
        await self.refused(env.sql("update salon_expense_rules set active = false where id = :i", i=rid))

    @pytest.mark.parametrize("over", [{"title": "   "}, {"freq": "yearly"}])
    async def test_bad_values_are_refused(self, env, over):
        f = await env.seed()
        await self.refused(self.insert(env, f["salon"], **over))

    async def test_the_same_key_cannot_be_used_twice_in_a_salon(self, env):
        f = await env.seed()
        await self.insert(env, f["salon"], k="same-key-123")
        await self.refused(self.insert(env, f["salon"], k="same-key-123"))

    async def test_public_roles_have_no_access_and_nobody_can_truncate(self, env):
        for role in ("anon", "authenticated"):
            row = (await env.sql("select has_table_privilege(:r, 'public.salon_expense_rules', 'SELECT') as s", r=role))[0]
            assert row["s"] is False
        row = (await env.sql("select has_table_privilege('service_role', 'public.salon_expense_rules', 'TRUNCATE') as t"))[0]
        assert row["t"] is False


def occurrence(created, day, **over):
    midnight = datetime.combine(day, datetime.min.time(), tzinfo=IST).isoformat()
    values = {"client_id": f"rule:{created['id']}:{day.isoformat()}", "title": created["title"],
              "category": created["category"], "amount_paise": created["amount_paise"],
              "payment_method": created["payment_method"], "occurred_at": midnight, "note": created["note"]}
    values.update(over)
    return values


async def record(http, item):
    return (await http.post("/v1/salons/me/expenses/batch", json={"items": [item]})).json()["results"][0]


async def test_a_stale_phone_cannot_record_days_the_rule_does_not_allow(env, monkeypatch):
    f = await trial_salon(env)
    other = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    start = today() - timedelta(days=10)
    async with http:
        weekly = (await http.post("/v1/salons/me/expense-rules", headers=key(),
                                  json=rule(frequency="weekly", start_date=start.isoformat()))).json()
        ok = await record(http, occurrence(weekly, start + timedelta(days=7)))
        assert ok["status"] == "created"
        wrong_day = await record(http, occurrence(weekly, start + timedelta(days=8)))  # not on the weekday
        before_start = await record(http, occurrence(weekly, start - timedelta(days=7)))
        wrong_amount = await record(http, occurrence(weekly, start, amount_paise=1))
        wrong_title = await record(http, occurrence(weekly, start, title="Something else"))
        date_mismatch = await record(http, occurrence(weekly, start, occurred_at=datetime.combine(
            start + timedelta(days=1), datetime.min.time(), tzinfo=IST).isoformat()))
        unknown = await record(http, {**occurrence(weekly, start), "client_id": f"rule:{uuid4()}:{start.isoformat()}"})
        malformed = await record(http, {**occurrence(weekly, start), "client_id": "rule:not-a-uuid:2026-01-01"})
        for refused in (wrong_day, before_start, wrong_amount, wrong_title, date_mismatch, unknown, malformed):
            assert refused["status"] == "rejected" and refused["code"] == "rule_occurrence_invalid", refused

        # Stop it; a later day is refused, a day up to the stop day still replays.
        await http.post(f"/v1/salons/me/expense-rules/{weekly['id']}/stop")
        after_stop = await record(http, occurrence(weekly, start + timedelta(days=14)))
        assert after_stop["status"] == "rejected" and after_stop["code"] == "rule_occurrence_invalid"
        assert (await record(http, occurrence(weekly, start + timedelta(days=7))))["status"] == "replayed"

    # Another salon's rule is not a rule here.
    http, _ = await client_for(env, monkeypatch, make_owner(other["owner"]))
    async with http:
        crossed = await record(http, occurrence(weekly, start + timedelta(days=7)))
        assert crossed["status"] == "rejected" and crossed["code"] == "rule_occurrence_invalid"
    assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s", s=other["salon"]))[0]["n"] == 0


async def test_a_retry_of_an_old_create_still_replays_after_its_start_date_left_the_window(env):
    """The window check is for new rules only: the same request two days later is still the same rule."""
    from app.application.use_cases.expense_rules import ExpenseRuleUseCases
    from app.infrastructure.db.repositories.expense_rule_repository import ExpenseRuleRepository

    f = await trial_salon(env)
    owner = make_owner(f["owner"])
    now = datetime.now(UTC)
    start = today() - timedelta(days=31)
    kwargs = {"title": "Rent", "category": "rent", "amount_paise": 1000, "payment_method": "cash", "note": None,
              "frequency": "monthly", "start_date": start, "idempotency_key": "late-retry-" + uuid4().hex}
    async with env.session() as session:
        first = await ExpenseRuleUseCases(ExpenseRuleRepository(session), lambda: now).add_rule(owner, **kwargs)
    async with env.session() as session:
        later = ExpenseRuleUseCases(ExpenseRuleRepository(session), lambda: now + timedelta(days=2))
        again = await later.add_rule(owner, **kwargs)
        assert again["id"] == first["id"] and again["replayed"] is True
        with pytest.raises(Exception) as caught:  # a NEW rule with that start is now outside the window
            await later.add_rule(owner, **{**kwargs, "idempotency_key": "other-key-" + uuid4().hex})
        assert "31 days" in str(caught.value)


async def test_the_stop_day_is_in_salon_time_and_a_phone_cannot_use_the_single_endpoint_to_skip_the_check(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    start = today() - timedelta(days=6)
    stop_day = start + timedelta(days=2)
    async with http:
        daily = (await http.post("/v1/salons/me/expense-rules", headers=key(),
                                 json=rule(frequency="daily", start_date=start.isoformat()))).json()
        # Stopped at 00:30 on the stop day in India: still the previous day in UTC.
        stopped_at = datetime.combine(stop_day, datetime.min.time(), tzinfo=IST) + timedelta(minutes=30)
        await env.sql("update salon_expense_rules set active = false, stopped_at = :t where id = :i",
                      t=stopped_at, i=daily["id"])
        assert stopped_at.astimezone(UTC).date() == stop_day - timedelta(days=1)
        assert (await record(http, occurrence(daily, stop_day)))["status"] == "created"  # the stop day itself
        refused = await record(http, occurrence(daily, stop_day + timedelta(days=1)))
        assert refused["status"] == "rejected" and refused["code"] == "rule_occurrence_invalid"

        sneaky = await http.post("/v1/salons/me/expenses", headers={"Idempotency-Key": f"rule:{daily['id']}:{start}"},
                                 json={"title": "Rent", "category": "rent", "amount_paise": 1, "payment_method": "cash",
                                       "occurred_at": datetime.now(UTC).isoformat()})
        assert sneaky.status_code == 422
        assert (await env.sql("select count(*) as n from salon_expenses where salon_id = :s and amount_paise = 1", s=f["salon"]))[0]["n"] == 0


class TestRuleCreatorErasure:
    async def test_deleting_the_creators_profile_clears_created_by_and_nothing_else_may_change(self, env):
        f = await env.seed()
        creator = str(uuid4())
        await env.sql("insert into auth.users(id, email) values(:i, :e)", i=creator, e=creator + "@example.test")
        rows = await env.sql(
            """insert into salon_expense_rules(salon_id, title, category, amount_paise, payment_method, frequency,
                 start_date, created_by, idempotency_key, request_hash)
               values(:s, 'Rent', 'rent', 1000, 'cash', 'monthly', current_date, :c, :k, repeat('a', 64)) returning id""",
            s=f["salon"], c=creator, k="rule-" + uuid4().hex)
        rid = str(rows[0]["id"])
        with pytest.raises((DBAPIError, IntegrityError)):
            await env.sql("update salon_expense_rules set created_by = :o where id = :i", o=f["owner"], i=rid)
        await env.sql("delete from profiles where id = :i", i=creator)
        row = (await env.sql("select created_by, active, amount_paise from salon_expense_rules where id = :i", i=rid))[0]
        assert row["created_by"] is None and row["active"] is True and row["amount_paise"] == 1000

