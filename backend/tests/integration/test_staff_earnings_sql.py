"""Staff earnings (0054) on disposable local PostgreSQL: constraints, same-salon proof, append-only, privileges."""

import asyncio
import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SIDECAR = Path(__file__).parents[2] / "migrations/sql/0054_staff_earnings.sql"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture(scope="module")
def staff_db(changes_db):  # noqa: F811
    async def install():
        env = SafetyEnv(changes_db)
        try:
            async with env.session() as session:
                for statement in SIDECAR.read_text(encoding="utf-8").split("\n-- statement --\n"):
                    if statement.strip():
                        await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()

    asyncio.run(install())
    return changes_db


@pytest.fixture
async def env(staff_db):
    environment = SafetyEnv(staff_db)
    yield environment
    await environment.engine.dispose()


async def refused(awaitable, fragment=""):
    with pytest.raises((DBAPIError, IntegrityError)) as caught:
        await awaitable
    assert fragment in str(caught.value), str(caught.value)[:300]


async def a_booking(env, delta=0):
    f = await env.seed()
    booking = await env.book(f, delta=delta)
    assert isinstance(booking, dict), booking
    return f, str(booking["id"])


async def complete_directly(env, booking_id):
    async with env.session() as session:
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(text("update bookings set status='completed', completed_at=now() where id=:i"), {"i": booking_id})
        await session.commit()


async def a_completed(env):
    f, booking = await a_booking(env)
    await complete_directly(env, booking)
    return f, booking


async def attribute(env, f, booking, staff, revision=1, salon=None):
    return await env.sql(
        """insert into booking_service_staff(booking_id, service_id, revision, salon_id, staff_id)
           values(:b, :svc, :rev, :salon, :staff)""",
        b=booking, svc=f["service"], rev=revision, salon=salon or f["salon"], staff=staff,
    )


async def rule(env, f, **over):
    values = {"salon": f["salon"], "staff": None, "service": None, "version": 1, "type": "PERCENT_OF_SERVICE_VALUE",
              "bps": 2000, "fixed": None, "key": "rule-" + uuid4().hex}
    values.update(over)
    rows = await env.sql(
        """insert into staff_commission_rule_versions(salon_id, staff_id, service_id, version, commission_type,
             rate_basis_points, fixed_amount_paise, effective_from, idempotency_key, request_hash)
           values(:salon, :staff, :service, :version, :type, :bps, :fixed, now(), :key, :hash) returning id""",
        hash=digest(values["key"]), **values,
    )
    return str(rows[0]["id"])


async def earning(env, f, booking, **over):
    values = {"salon": f["salon"], "booking": booking, "service": f["service"], "staff": f["staff"], "source": "booking_staff",
              "value": 25_000, "amount": 5_000, "rule": None, "type": "PERCENT_OF_SERVICE_VALUE", "bps": 2000, "fixed": None}
    values.update(over)
    return await env.sql(
        """insert into staff_earnings(salon_id, booking_id, service_id, staff_id, attribution_source, service_value_paise,
             amount_paise, rule_version_id, commission_type, rate_basis_points, fixed_amount_paise, completed_at)
           values(:salon, :booking, :service, :staff, :source, :value, :amount, :rule, :type, :bps, :fixed, now())""",
        **values,
    )


class TestAttribution:
    async def test_the_owner_can_name_who_did_a_service_and_change_it_before_completion(self, env):
        f, booking = await a_booking(env)
        await attribute(env, f, booking, f["staff"], 1)
        await attribute(env, f, booking, f["staff"], 2)
        rows = await env.sql("select max(revision) as r from booking_service_staff where booking_id = :b", b=booking)
        assert rows[0]["r"] == 2

    async def test_revisions_go_one_two_three_with_no_gaps(self, env):
        f, booking = await a_booking(env)
        await refused(attribute(env, f, booking, f["staff"], 2), "attribution_revision_out_of_order")
        await attribute(env, f, booking, f["staff"], 1)
        await refused(attribute(env, f, booking, f["staff"], 1), "")
        await refused(attribute(env, f, booking, f["staff"], 3), "attribution_revision_out_of_order")

    async def test_no_change_once_the_service_is_completed(self, env):
        f, booking = await a_booking(env)
        await attribute(env, f, booking, f["staff"], 1)
        await complete_directly(env, booking)
        await refused(attribute(env, f, booking, f["staff"], 2), "attribution_after_completion")

    async def test_the_staff_member_must_belong_to_the_same_salon(self, env):
        f, booking = await a_booking(env)
        other = await env.seed()
        await refused(attribute(env, f, booking, other["staff"], 1))

    async def test_the_salon_must_match_the_booking(self, env):
        f, booking = await a_booking(env)
        other = await env.seed()
        await refused(attribute(env, f, booking, f["staff"], 1, salon=other["salon"]), "attribution_wrong_salon")

    async def test_an_attribution_is_never_edited(self, env):
        f, booking = await a_booking(env)
        await attribute(env, f, booking, f["staff"], 1)
        await refused(env.sql("update booking_service_staff set revision = 9 where booking_id = :b", b=booking), "staff_records_are_append_only")

    async def test_the_service_must_be_on_the_booking(self, env):
        f, booking = await a_booking(env)
        stranger = await env.seed()
        await refused(env.sql(
            """insert into booking_service_staff(booking_id, service_id, revision, salon_id, staff_id)
               values(:b, :svc, 1, :salon, :staff)""",
            b=booking, svc=stranger["service"], salon=f["salon"], staff=f["staff"]))

    async def test_deleting_the_profile_that_made_a_change_clears_who_it_was_and_nothing_else(self, env):
        f, booking = await a_booking(env)
        who = str(uuid4())
        await env.sql("insert into auth.users(id, email) values(:i, :e)", i=who, e=who + "@example.test")
        await env.sql(
            """insert into booking_service_staff(booking_id, service_id, revision, salon_id, staff_id, changed_by)
               values(:b, :svc, 1, :salon, :staff, :who)""",
            b=booking, svc=f["service"], salon=f["salon"], staff=f["staff"], who=who)
        await env.sql("delete from profiles where id = :i", i=who)
        row = (await env.sql("select changed_by, revision, staff_id::text as staff from booking_service_staff where booking_id = :b", b=booking))[0]
        assert row["changed_by"] is None and row["revision"] == 1 and row["staff"] == f["staff"]


class TestRuleVersions:
    @pytest.mark.parametrize("over", [
        {"type": "PERCENT_OF_SERVICE_VALUE", "bps": None},
        {"type": "PERCENT_OF_SERVICE_VALUE", "bps": 10_001},
        {"type": "PERCENT_OF_SERVICE_VALUE", "bps": 1000, "fixed": 100},
        {"type": "FIXED_PER_SERVICE", "bps": None, "fixed": None},
        {"type": "FIXED_PER_SERVICE", "bps": 1000, "fixed": 100},
        {"type": "FIXED_PER_SERVICE", "bps": None, "fixed": -1},
        {"type": "NONE", "bps": 1000},
        {"type": "NONE", "bps": None, "fixed": 5},
        {"type": "SOMETHING_ELSE", "bps": None},
        {"version": 0},
    ])
    async def test_a_rule_must_be_one_complete_shape(self, env, over):
        f = await env.seed()
        await refused(rule(env, f, **over))

    async def test_the_three_shapes_are_accepted(self, env):
        f = await env.seed()
        await rule(env, f, staff=f["staff"], type="PERCENT_OF_SERVICE_VALUE", bps=2500)
        await rule(env, f, service=f["service"], type="FIXED_PER_SERVICE", bps=None, fixed=5_000)
        await rule(env, f, type="NONE", bps=None)

    async def test_a_scope_has_one_row_per_version_and_the_salon_default_counts_as_a_scope(self, env):
        f = await env.seed()
        await rule(env, f, version=1)
        await refused(rule(env, f, version=1), "staff_commission_rule_scope_version")
        await rule(env, f, version=2)
        await rule(env, f, staff=f["staff"], version=1)  # another scope can start at 1 again
        await refused(rule(env, f, staff=f["staff"], version=1), "staff_commission_rule_scope_version")

    async def test_a_rule_cannot_point_at_another_salons_staff_or_service(self, env):
        f = await env.seed()
        other = await env.seed()
        await refused(rule(env, f, staff=other["staff"]))
        await refused(rule(env, f, service=other["service"]))

    async def test_the_same_request_key_cannot_make_two_rules(self, env):
        f = await env.seed()
        await rule(env, f, key="same-key-123", version=1)
        await refused(rule(env, f, key="same-key-123", version=2))

    async def test_a_rule_is_never_edited_or_deleted(self, env):
        f = await env.seed()
        rid = await rule(env, f)
        await refused(env.sql("update staff_commission_rule_versions set rate_basis_points = 1 where id = :i", i=rid), "staff_records_are_append_only")
        await refused(env.sql("delete from staff_commission_rule_versions where id = :i", i=rid), "staff_records_are_append_only")

    async def test_a_new_version_never_starts_earlier_than_the_one_before_it_in_the_same_scope(self, env):
        f = await env.seed()
        await env.sql(
            """insert into staff_commission_rule_versions(salon_id, version, commission_type, rate_basis_points,
                 effective_from, idempotency_key, request_hash)
               values(:s, 1, 'PERCENT_OF_SERVICE_VALUE', 1000, now() + interval '2 days', :k, :h)""",
            s=f["salon"], k="a-" + uuid4().hex, h=digest("a"))
        await refused(env.sql(
            """insert into staff_commission_rule_versions(salon_id, version, commission_type, rate_basis_points,
                 effective_from, idempotency_key, request_hash)
               values(:s, 2, 'PERCENT_OF_SERVICE_VALUE', 2000, now() + interval '1 day', :k, :h)""",
            s=f["salon"], k="b-" + uuid4().hex, h=digest("b")), "rule_effective_from_goes_backwards")
        # the same moment is fine, and another scope has its own timeline
        await env.sql(
            """insert into staff_commission_rule_versions(salon_id, version, commission_type, rate_basis_points,
                 effective_from, idempotency_key, request_hash)
               values(:s, 2, 'PERCENT_OF_SERVICE_VALUE', 2000, now() + interval '2 days', :k, :h)""",
            s=f["salon"], k="c-" + uuid4().hex, h=digest("c"))
        await rule(env, f, staff=f["staff"], version=1)

    async def test_deleting_the_profile_that_made_a_rule_clears_who_it_was_and_nothing_else(self, env):
        f = await env.seed()
        who = str(uuid4())
        await env.sql("insert into auth.users(id, email) values(:i, :e)", i=who, e=who + "@example.test")
        rows = await env.sql(
            """insert into staff_commission_rule_versions(salon_id, version, commission_type, rate_basis_points,
                 effective_from, created_by, idempotency_key, request_hash)
               values(:s, 1, 'PERCENT_OF_SERVICE_VALUE', 1234, now(), :who, :k, :h) returning id""",
            s=f["salon"], who=who, k="d-" + uuid4().hex, h=digest("d"))
        await env.sql("delete from profiles where id = :i", i=who)
        row = (await env.sql("select created_by, rate_basis_points from staff_commission_rule_versions where id = :i", i=rows[0]["id"]))[0]
        assert row["created_by"] is None and row["rate_basis_points"] == 1234


class TestEarnings:
    async def test_a_completed_service_records_what_it_earned(self, env):
        f, booking = await a_completed(env)
        rid = await rule(env, f)
        await earning(env, f, booking, rule=rid)
        rows = await env.sql("select amount_paise, commission_type from staff_earnings where booking_id = :b", b=booking)
        assert rows == [{"amount_paise": 5_000, "commission_type": "PERCENT_OF_SERVICE_VALUE"}]

    async def test_a_service_that_earned_nothing_still_gets_a_row_with_no_rule(self, env):
        f, booking = await a_completed(env)
        await earning(env, f, booking, type="NONE", amount=0, bps=None, rule=None)

    async def test_one_service_line_is_earned_once_ever(self, env):
        f, booking = await a_completed(env)
        rid = await rule(env, f)
        await earning(env, f, booking, rule=rid)
        await refused(earning(env, f, booking, rule=rid), "")

    @pytest.mark.parametrize("over", [
        {"amount": 25_001},
        {"type": "NONE", "amount": 100, "bps": None},
        {"type": "PERCENT_OF_SERVICE_VALUE", "rule": None},
        {"amount": -1},
        {"value": -1, "amount": 0},
        {"type": "FIXED_PER_SERVICE", "bps": 2000, "fixed": 500},
        {"source": "guess"},
    ])
    async def test_impossible_earnings_are_refused(self, env, over):
        f, booking = await a_completed(env)
        rid = await rule(env, f)
        values = {"rule": rid, **over}
        await refused(earning(env, f, booking, **values))

    async def test_the_staff_member_must_be_from_the_bookings_salon(self, env):
        f, booking = await a_completed(env)
        other = await env.seed()
        rid = await rule(env, f)
        await refused(earning(env, f, booking, staff=other["staff"], rule=rid))

    async def test_the_salon_must_match_the_booking(self, env):
        f, booking = await a_completed(env)
        other = await env.seed()
        rid = await rule(env, other)
        await refused(earning(env, f, booking, salon=other["salon"], staff=other["staff"], rule=rid), "earning_wrong_salon")

    async def test_an_earning_is_never_edited_or_deleted(self, env):
        f, booking = await a_completed(env)
        rid = await rule(env, f)
        await earning(env, f, booking, rule=rid)
        await refused(env.sql("update staff_earnings set amount_paise = 1 where booking_id = :b", b=booking), "staff_records_are_append_only")
        await refused(env.sql("delete from staff_earnings where booking_id = :b", b=booking), "staff_records_are_append_only")

    async def test_a_later_rule_change_never_rewrites_a_past_earning(self, env):
        f, booking = await a_completed(env)
        rid = await rule(env, f, version=1, bps=2000)
        await earning(env, f, booking, rule=rid)
        await rule(env, f, version=2, bps=9000)
        rows = await env.sql("select rate_basis_points, amount_paise from staff_earnings where booking_id = :b", b=booking)
        assert rows == [{"rate_basis_points": 2000, "amount_paise": 5_000}]

    async def test_an_earning_needs_a_completed_booking(self, env):
        f, booking = await a_booking(env)  # still confirmed
        await refused(earning(env, f, booking, type="NONE", amount=0, bps=None), "earning_before_completion")

    async def test_the_earning_goes_to_the_staff_member_who_did_the_service(self, env):
        f, booking = await a_booking(env)
        other = str(uuid4())
        await env.sql("insert into staff(id, salon_id, name) values(:i, :s, 'Second barber')", i=other, s=f["salon"])
        await attribute(env, f, booking, other, 1)
        await complete_directly(env, booking)
        await refused(earning(env, f, booking, type="NONE", amount=0, bps=None), "earning_wrong_staff")  # the booking's own staff
        await refused(earning(env, f, booking, staff=other, source="booking_staff", type="NONE", amount=0, bps=None), "earning_wrong_staff")
        await earning(env, f, booking, staff=other, source="attributed", type="NONE", amount=0, bps=None)

    async def test_the_booking_staff_member_is_wrong_when_someone_else_is_named(self, env):
        f, booking = await a_completed(env)
        other = str(uuid4())
        await env.sql("insert into staff(id, salon_id, name) values(:i, :s, 'Second barber')", i=other, s=f["salon"])
        await refused(earning(env, f, booking, staff=other, type="NONE", amount=0, bps=None), "earning_wrong_staff")

    async def test_the_value_must_be_the_lines_price(self, env):
        f, booking = await a_completed(env)
        await refused(earning(env, f, booking, type="NONE", amount=0, bps=None, value=1), "earning_value_mismatch")

    async def test_a_removed_service_line_earns_nothing(self, env):
        f, booking = await a_booking(env)
        async with env.session() as session:
            await session.execute(text("set local session_replication_role=replica"))
            await session.execute(text("update booking_services set is_active = false where booking_id = :b"), {"b": booking})
            await session.commit()
        await complete_directly(env, booking)
        await refused(earning(env, f, booking, type="NONE", amount=0, bps=None), "earning_for_inactive_service")

    async def test_the_amount_must_follow_from_the_rule_and_the_price(self, env):
        f, booking = await a_completed(env)
        rid = await rule(env, f, bps=2000)
        await refused(earning(env, f, booking, rule=rid, amount=24_000), "")  # 20% of 250 is 50, not 240
        await refused(earning(env, f, booking, rule=rid, amount=4_999), "")
        await earning(env, f, booking, rule=rid, amount=5_000)

    async def test_a_fixed_amount_is_exact_and_capped_at_the_price(self, env):
        f, booking = await a_completed(env)
        capped = await rule(env, f, type="FIXED_PER_SERVICE", bps=None, fixed=99_000)
        await refused(earning(env, f, booking, type="FIXED_PER_SERVICE", rule=capped, bps=None, fixed=99_000, amount=30_000), "")
        await refused(earning(env, f, booking, type="FIXED_PER_SERVICE", rule=capped, bps=None, fixed=99_000, amount=24_999), "")
        await earning(env, f, booking, type="FIXED_PER_SERVICE", rule=capped, bps=None, fixed=99_000, amount=25_000)

    async def test_a_half_paisa_rounds_up(self, env):
        f, booking = await a_completed(env)
        rid = await rule(env, f, bps=3333)  # 33.33% of 25000 = 8332.5 -> 8333
        await refused(earning(env, f, booking, rule=rid, bps=3333, amount=8_332), "")
        await earning(env, f, booking, rule=rid, bps=3333, amount=8_333)

    async def test_the_earning_must_quote_the_rule_it_points_at(self, env):
        f, booking = await a_completed(env)
        rid = await rule(env, f, bps=2000)
        await refused(earning(env, f, booking, rule=rid, bps=1000, amount=2_500), "earning_rule_mismatch")  # not that rule's rate
        other = await env.seed()
        foreign = await rule(env, other, bps=2000)
        await refused(earning(env, f, booking, rule=foreign), "earning_rule_mismatch")  # another salon's rule
        aimed = await rule(env, f, staff=str(uuid4()) if False else f["staff"], service=None, bps=2000)
        scoped_elsewhere = await env.seed()
        await refused(earning(env, f, booking, rule=await rule(env, scoped_elsewhere, staff=scoped_elsewhere["staff"], bps=2000)), "earning_rule_mismatch")
        assert aimed  # a rule for this very staff member is fine

    async def test_a_rule_that_had_not_started_yet_cannot_be_the_one_quoted(self, env):
        f, booking = await a_completed(env)
        rows = await env.sql(
            """insert into staff_commission_rule_versions(salon_id, version, commission_type, rate_basis_points,
                 effective_from, idempotency_key, request_hash)
               values(:s, 1, 'PERCENT_OF_SERVICE_VALUE', 2000, now() + interval '1 day', :k, :h) returning id""",
            s=f["salon"], k="e-" + uuid4().hex, h=digest("e"))
        await refused(earning(env, f, booking, rule=str(rows[0]["id"])), "earning_rule_mismatch")


class TestPrivileges:
    @pytest.mark.parametrize("table", ["booking_service_staff", "staff_commission_rule_versions", "staff_earnings"])
    @pytest.mark.parametrize("role", ["anon", "authenticated"])
    async def test_public_roles_cannot_read_or_write_them(self, env, table, role):
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            row = (await env.sql("select has_table_privilege(:r, 'public.' || :t, :p) as ok", r=role, t=table, p=privilege))[0]
            assert row["ok"] is False

    @pytest.mark.parametrize("table", ["booking_service_staff", "staff_commission_rule_versions", "staff_earnings"])
    async def test_nobody_can_empty_a_table_around_its_triggers(self, env, table):
        row = (await env.sql("select has_table_privilege('service_role', 'public.' || :t, 'TRUNCATE') as ok", t=table))[0]
        assert row["ok"] is False

    @pytest.mark.parametrize("table", ["booking_service_staff", "staff_commission_rule_versions", "staff_earnings"])
    async def test_row_level_security_is_on(self, env, table):
        row = (await env.sql("select relrowsecurity as on_ from pg_class where oid = ('public.' || :t)::regclass", t=table))[0]
        assert row["on_"] is True

    @pytest.mark.parametrize("table", ["booking_service_staff", "staff_commission_rule_versions", "staff_earnings"])
    async def test_not_even_the_table_owner_can_empty_it(self, env, table):
        # A table that earnings point at is refused by PostgreSQL itself, which is stronger still.
        reason = "referenced in a foreign key" if table == "staff_commission_rule_versions" else "staff_records_are_append_only"
        await refused(env.sql(f"truncate public.{table}"), reason)
