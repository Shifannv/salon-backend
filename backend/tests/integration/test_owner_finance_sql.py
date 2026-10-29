"""Owner finance cash book (0051) on disposable local PostgreSQL: constraints, triggers, privileges."""

import asyncio
import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SIDECAR = Path(__file__).parents[2] / "migrations/sql/0051_owner_finance_cashbook.sql"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture(scope="module")
def cashbook_db(changes_db):  # noqa: F811
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
async def env(cashbook_db):
    environment = SafetyEnv(cashbook_db)
    yield environment
    await environment.engine.dispose()


async def expense(env, salon, **overrides):
    """Insert one expense row. A reversal takes the original's date unless ``at`` says otherwise."""
    values = {
        "salon": salon, "kind": "expense", "reverses": None, "category": "supplies", "amount": 5000,
        "method": "cash", "note": "towels", "title": "Towels", "by": None, "key": "key-" + uuid4().hex,
        "at": None,
    }
    values.update(overrides)
    rows = await env.sql(
        """insert into salon_expenses(salon_id, entry_type, reverses_id, category, amount_paise,
             payment_method, occurred_at, note, title, created_by, idempotency_key, request_hash)
           values(:salon, :kind, :reverses, :category, :amount, :method,
                  coalesce(cast(:at as timestamptz),
                           (select occurred_at from salon_expenses where id = :reverses), now()),
                  :note, :title, :by, :key, :hash)
           returning id""",
        hash=digest(values["key"]), **values,
    )
    return str(rows[0]["id"])


async def refused(awaitable, fragment):
    with pytest.raises((DBAPIError, IntegrityError)) as caught:
        await awaitable
    assert fragment in str(caught.value), str(caught.value)[:300]


class TestExpenses:
    async def test_an_expense_and_its_exact_reversal_are_recorded(self, env):
        f = await env.seed()
        original = await expense(env, f["salon"])
        reversal = await expense(env, f["salon"], kind="reversal", reverses=original, note=None)
        assert reversal != original

    async def test_a_reversal_must_mirror_the_original_exactly(self, env):
        f = await env.seed()
        original = await expense(env, f["salon"])
        await refused(expense(env, f["salon"], kind="reversal", reverses=original, amount=4999),
                      "expense_reversal_mismatch")
        await refused(expense(env, f["salon"], kind="reversal", reverses=original, method="non_cash"),
                      "expense_reversal_mismatch")
        await refused(expense(env, f["salon"], kind="reversal", reverses=original, category="rent"),
                      "expense_reversal_mismatch")

    async def test_an_expense_is_reversed_at_most_once(self, env):
        f = await env.seed()
        original = await expense(env, f["salon"])
        await expense(env, f["salon"], kind="reversal", reverses=original)
        await refused(expense(env, f["salon"], kind="reversal", reverses=original), "reverses_id")

    async def test_a_reversal_lands_on_the_same_day_as_the_expense_it_cancels(self, env):
        f = await env.seed()
        original = await expense(env, f["salon"], at=datetime(2026, 10, 27, 6, 30, tzinfo=UTC))
        await refused(
            expense(env, f["salon"], kind="reversal", reverses=original, at=datetime(2026, 10, 29, 6, 30, tzinfo=UTC)),
            "expense_reversal_mismatch",
        )
        reversal = await expense(env, f["salon"], kind="reversal", reverses=original)  # inherits the date
        rows = await env.sql("select occurred_at from salon_expenses where id in (:a, :b)", a=original, b=reversal)
        assert len({row["occurred_at"] for row in rows}) == 1

    async def test_a_reversal_must_carry_the_same_name(self, env):
        f = await env.seed()
        original = await expense(env, f["salon"], title="Tea")
        await refused(expense(env, f["salon"], kind="reversal", reverses=original, title="Coffee"),
                      "expense_reversal_mismatch")
        await expense(env, f["salon"], kind="reversal", reverses=original, title="Tea")

    @pytest.mark.parametrize("title", ["", "   ", None, "x" * 81])
    async def test_every_expense_needs_a_name_of_one_to_eighty_characters(self, env, title):
        f = await env.seed()
        await refused(expense(env, f["salon"], title=title), "title")

    async def test_a_name_of_eighty_characters_is_accepted(self, env):
        f = await env.seed()
        await expense(env, f["salon"], title="x" * 80)

    async def test_the_change_sequence_only_ever_goes_up_per_salon_and_cannot_be_chosen(self, env):
        f = await env.seed()
        first, second = await expense(env, f["salon"]), await expense(env, f["salon"])
        rows = await env.sql(
            "select id, seq from salon_expenses where id in (:a, :b) order by seq", a=first, b=second)
        assert [str(r["id"]) for r in rows] == [first, second]
        assert rows[0]["seq"] < rows[1]["seq"]
        await refused(env.sql(
            """insert into salon_expenses(salon_id, seq, entry_type, category, amount_paise, payment_method,
                 occurred_at, title, idempotency_key, request_hash)
               values(:s, 5, 'expense', 'other', 100, 'cash', now(), 'x', 'seq-key-1234', :h)""",
            s=f["salon"], h=digest("seq-key-1234")), "seq")

    async def test_a_reversal_cannot_target_another_salons_expense(self, env):
        mine, theirs = await env.seed(), await env.seed()
        original = await expense(env, theirs["salon"])
        await refused(expense(env, mine["salon"], kind="reversal", reverses=original),
                      "expense_reversal_mismatch")

    async def test_a_reversal_cannot_reverse_a_reversal(self, env):
        f = await env.seed()
        original = await expense(env, f["salon"])
        reversal = await expense(env, f["salon"], kind="reversal", reverses=original)
        await refused(expense(env, f["salon"], kind="reversal", reverses=reversal),
                      "expense_reversal_mismatch")

    @pytest.mark.parametrize("amount", [0, -1])
    async def test_amounts_must_be_positive(self, env, amount):
        f = await env.seed()
        await refused(expense(env, f["salon"], amount=amount), "amount_paise")

    async def test_category_and_method_are_closed_lists(self, env):
        f = await env.seed()
        await refused(expense(env, f["salon"], category="bribes"), "category")
        await refused(expense(env, f["salon"], method="crypto"), "payment_method")

    async def test_a_repeated_idempotency_key_cannot_create_a_second_row(self, env):
        f = await env.seed()
        await expense(env, f["salon"], key="same-key-123")
        await refused(expense(env, f["salon"], key="same-key-123"), "idempotency_key")
        other = await env.seed()
        await expense(env, other["salon"], key="same-key-123")  # keys are per salon

    async def test_a_plain_entry_cannot_name_a_target_and_a_reversal_needs_one(self, env):
        f = await env.seed()
        original = await expense(env, f["salon"])
        await refused(expense(env, f["salon"], kind="expense", reverses=original), "check")
        # The mirror trigger runs before the CHECK, so this is refused with its own message.
        await refused(expense(env, f["salon"], kind="reversal", reverses=None), "expense_reversal_mismatch")


class TestAppendOnly:
    @pytest.mark.parametrize("role", ["postgres", "service_role"])
    @pytest.mark.parametrize("table", ["salon_expenses", "salon_cash_adjustments", "salon_day_closes"])
    async def test_truncate_is_refused_even_for_owner_and_backend_roles(self, env, role, table):
        f = await env.seed()
        if table == "salon_expenses":
            await expense(env, f["salon"])
        elif table == "salon_cash_adjustments":
            await adjustment(env, f["salon"])
        else:
            await close(env, f["salon"])
        before = (await env.sql(f"select count(*) as n from {table}"))[0]["n"]
        async with env.session() as session:
            await session.execute(text(f"set local role {role}"))
            message = "finance_records_are_append_only" if role == "postgres" else "permission denied"
            with pytest.raises(DBAPIError, match=message):
                await session.execute(text(f"truncate table {table}"))
            await session.rollback()
        after = (await env.sql(f"select count(*) as n from {table}"))[0]["n"]
        assert after == before

    async def test_rows_cannot_be_edited_or_deleted(self, env):
        f = await env.seed()
        row = await expense(env, f["salon"])
        await refused(env.sql("update salon_expenses set amount_paise = 1 where id = :i", i=row),
                      "finance_records_are_append_only")
        await refused(env.sql("update salon_expenses set category = 'rent' where id = :i", i=row),
                      "finance_records_are_append_only")
        await refused(env.sql("delete from salon_expenses where id = :i", i=row),
                      "finance_records_are_append_only")

    async def test_free_text_can_be_redacted_only_inside_an_erasure_transaction(self, env):
        f = await env.seed()
        row = await expense(env, f["salon"], note="advance to Hafis", title="Hafis advance")
        await refused(env.sql("update salon_expenses set note = null where id = :i", i=row),
                      "finance_records_are_append_only")
        await refused(env.sql("update salon_expenses set title = 'Removed' where id = :i", i=row),
                      "finance_records_are_append_only")
        async with env.session() as session:
            await session.execute(text("select set_config('app.finance_redaction', 'on', true)"))
            await session.execute(
                text("update salon_expenses set note = null, title = 'Removed' where id = :i"), {"i": row})
            await session.commit()
        assert (await env.sql("select note, title, amount_paise from salon_expenses where id = :i", i=row))[0] == {
            "note": None, "title": "Removed", "amount_paise": 5000,
        }

    async def test_redaction_can_only_blank_text_it_can_never_write_new_text(self, env):
        f = await env.seed()
        row = await expense(env, f["salon"], note="advance to Hafis", title="Hafis advance")
        async with env.session() as session:
            await session.execute(text("select set_config('app.finance_redaction', 'on', true)"))
            for statement in ("update salon_expenses set note = 'rewritten history' where id = :i",
                              "update salon_expenses set title = 'Something else' where id = :i"):
                with pytest.raises((DBAPIError, IntegrityError)) as caught:
                    await session.execute(text(statement), {"i": row})
                assert "finance_records_are_append_only" in str(caught.value)
                await session.rollback()
                await session.execute(text("select set_config('app.finance_redaction', 'on', true)"))
            await session.execute(text("update salon_expenses set note = null, title = 'Removed' where id = :i"), {"i": row})
            await session.commit()

    async def test_redaction_permission_does_not_unlock_money_columns(self, env):
        f = await env.seed()
        row = await expense(env, f["salon"])
        async with env.session() as session:
            await session.execute(text("select set_config('app.finance_redaction', 'on', true)"))
            with pytest.raises((DBAPIError, IntegrityError)) as caught:
                await session.execute(text("update salon_expenses set amount_paise = 1 where id = :i"), {"i": row})
            assert "finance_records_are_append_only" in str(caught.value)

    async def test_deleting_the_actors_profile_clears_created_by_and_keeps_the_money(self, env):
        f = await env.seed()
        row = await expense(env, f["salon"], by=f["customer"])
        assert (await env.sql("select created_by from salon_expenses where id = :i", i=row))[0]["created_by"]
        await env.sql("delete from profiles where id = :i", i=f["customer"])
        after = (await env.sql("select created_by, amount_paise from salon_expenses where id = :i", i=row))[0]
        assert after == {"created_by": None, "amount_paise": 5000}

    async def test_created_by_cannot_be_pointed_at_someone_else_later(self, env):
        f = await env.seed()
        row = await expense(env, f["salon"], by=f["customer"])
        await refused(env.sql("update salon_expenses set created_by = :o where id = :i", o=f["owner"], i=row),
                      "finance_records_are_append_only")


async def adjustment(env, salon, **overrides):
    values = {"salon": salon, "direction": "in", "amount": 2500, "reason": "Float top-up",
              "reverses": None, "key": "adj-" + uuid4().hex}
    values.update(overrides)
    rows = await env.sql(
        """insert into salon_cash_adjustments(salon_id, direction, amount_paise, reason, occurred_at,
             reverses_id, idempotency_key, request_hash)
           values(:salon, :direction, :amount, :reason, now(), :reverses, :key, :hash) returning id""",
        hash=digest(values["key"]), **values,
    )
    return str(rows[0]["id"])


class TestCashAdjustments:
    async def test_a_reason_is_mandatory(self, env):
        f = await env.seed()
        await refused(adjustment(env, f["salon"], reason="  "), "reason")
        await refused(adjustment(env, f["salon"], reason="ab"), "reason")

    async def test_a_correction_is_the_opposite_movement_of_the_same_amount(self, env):
        f = await env.seed()
        original = await adjustment(env, f["salon"])
        await refused(adjustment(env, f["salon"], reverses=original, direction="in"),
                      "cash_adjustment_reversal_mismatch")
        await refused(adjustment(env, f["salon"], reverses=original, direction="out", amount=1),
                      "cash_adjustment_reversal_mismatch")
        await adjustment(env, f["salon"], reverses=original, direction="out", reason="Entered twice")
        await refused(adjustment(env, f["salon"], reverses=original, direction="out"), "reverses_id")


async def close(env, salon, **overrides):
    values = {"salon": salon, "date": date(2026, 10, 29), "revision": 1, "opening": 100000, "expected": 125000,
              "actual": 125000, "reason": None, "by": None, "key": "close-" + uuid4().hex}
    values.update(overrides)
    rows = await env.sql(
        """insert into salon_day_closes(salon_id, local_date, revision, opening_cash_paise,
             expected_cash_paise, actual_cash_paise, difference_reason, created_by, idempotency_key, request_hash)
           values(:salon, :date, :revision, :opening, :expected, :actual, :reason, :by, :key, :hash)
           returning id, difference_paise""",
        hash=digest(values["key"]), **values,
    )
    return rows[0]


class TestDayCloses:
    async def test_the_difference_is_computed_by_the_database(self, env):
        f = await env.seed()
        row = await close(env, f["salon"], actual=124500, reason="Tip jar emptied")
        assert row["difference_paise"] == -500

    async def test_a_difference_needs_a_written_reason(self, env):
        f = await env.seed()
        await refused(close(env, f["salon"], actual=124500), "check")
        await refused(close(env, f["salon"], actual=124500, reason="  "), "check")
        await close(env, f["salon"], actual=125000)  # an exact count needs none

    async def test_revisions_are_sequential_and_never_overwrite(self, env):
        f = await env.seed()
        await close(env, f["salon"])
        await refused(close(env, f["salon"], revision=3), "day_close_revision_gap")
        await refused(close(env, f["salon"], revision=1), "day_close_revision_gap")
        await close(env, f["salon"], revision=2, actual=125500, reason="Recounted")
        await close(env, f["salon"], date=date(2026, 10, 30), revision=1)  # another day starts at 1

    async def test_a_close_reason_can_be_redacted_in_erasure_but_the_difference_cannot_change(self, env):
        f = await env.seed()
        row = await close(env, f["salon"], actual=124500, reason="Hafis took 500")
        async with env.session() as session:
            await session.execute(text("select set_config('app.finance_redaction', 'on', true)"))
            await session.execute(text("update salon_day_closes set difference_reason = 'Removed' where id = :i"),
                                  {"i": row["id"]})
            await session.commit()
        after = (await env.sql("select difference_reason, difference_paise from salon_day_closes where id = :i",
                               i=row["id"]))[0]
        assert after == {"difference_reason": "Removed", "difference_paise": -500}
        # Redaction permission still does not unlock the counted or expected amounts.
        async with env.session() as session:
            await session.execute(text("select set_config('app.finance_redaction', 'on', true)"))
            with pytest.raises((DBAPIError, IntegrityError)) as caught:
                await session.execute(text("update salon_day_closes set expected_cash_paise = 0 where id = :i"),
                                      {"i": row["id"]})
            assert "finance_records_are_append_only" in str(caught.value)

    async def test_deleting_the_actors_profile_keeps_the_close_and_its_difference(self, env):
        f = await env.seed()
        row = await close(env, f["salon"], actual=124500, reason="Counted twice", by=f["customer"])
        assert (await env.sql("select created_by from salon_day_closes where id = :i", i=row["id"]))[0]["created_by"]
        await env.sql("delete from profiles where id = :i", i=f["customer"])
        kept = (await env.sql("select difference_paise, created_by from salon_day_closes where id = :i", i=row["id"]))[0]
        assert kept == {"difference_paise": -500, "created_by": None}

    async def test_closed_days_cannot_be_edited(self, env):
        f = await env.seed()
        row = await close(env, f["salon"])
        await refused(env.sql("update salon_day_closes set actual_cash_paise = 1 where id = :i", i=row["id"]),
                      "finance_records_are_append_only")


class TestPrivileges:
    @pytest.mark.parametrize("table", ["salon_expenses", "salon_cash_adjustments", "salon_day_closes"])
    async def test_row_level_security_is_on_and_public_roles_have_no_access(self, env, table):
        row = (await env.sql(
            """select c.relrowsecurity as rls,
                      has_table_privilege('anon', c.oid, 'select') as anon_select,
                      has_table_privilege('authenticated', c.oid, 'insert') as auth_insert,
                      has_table_privilege('authenticated', c.oid, 'select') as auth_select
               from pg_class c where c.oid = to_regclass('public.' || :t)""", t=table))[0]
        assert row == {"rls": True, "anon_select": False, "auth_insert": False, "auth_select": False}

    async def test_the_new_tables_hold_only_expected_text_columns(self, env):
        rows = await env.sql(
            """select table_name || '.' || column_name as col from information_schema.columns
               where table_schema = 'public'
                 and table_name in ('salon_expenses','salon_cash_adjustments','salon_day_closes')
                 and data_type in ('text', 'character varying', 'jsonb')
               order by 1""")
        assert {r["col"] for r in rows} == {
            "salon_expenses.entry_type", "salon_expenses.category", "salon_expenses.payment_method",
            "salon_expenses.note", "salon_expenses.title", "salon_expenses.idempotency_key",
            "salon_expenses.request_hash",
            "salon_cash_adjustments.direction", "salon_cash_adjustments.reason",
            "salon_cash_adjustments.idempotency_key", "salon_cash_adjustments.request_hash",
            "salon_day_closes.difference_reason", "salon_day_closes.idempotency_key",
            "salon_day_closes.request_hash",
        }

    @pytest.mark.parametrize("table", ["salon_expenses", "salon_cash_adjustments", "salon_day_closes"])
    async def test_nobody_can_empty_a_finance_table_around_its_triggers(self, env, table):
        row = (await env.sql("select has_table_privilege('service_role', 'public.' || :t, 'TRUNCATE') as t", t=table))[0]
        assert row["t"] is False

    @pytest.mark.parametrize("role", ["anon", "authenticated"])
    async def test_public_roles_cannot_touch_the_change_sequence(self, env, role):
        row = (await env.sql(
            """select has_sequence_privilege(:r, pg_get_serial_sequence('public.salon_expenses', 'seq'), 'USAGE') as u,
                      has_sequence_privilege(:r, pg_get_serial_sequence('public.salon_expenses', 'seq'), 'SELECT') as s""",
            r=role))[0]
        assert row == {"u": False, "s": False}

    async def test_erasing_a_profile_does_not_scan_the_finance_tables(self, env):
        wanted = {"salon_expenses_created_by", "salon_cash_adjustments_created_by", "salon_day_closes_created_by"}
        rows = await env.sql(
            "select indexname from pg_indexes where schemaname = 'public' and indexname = any(cast(:names as text[]))",
            names=sorted(wanted))
        assert {r["indexname"] for r in rows} == wanted

    async def test_a_finance_write_lock_does_not_stall_bookings_or_payments(self, env):
        """Inserting a booking or payment takes FOR KEY SHARE on the salon; the finance lock must not block it."""
        from app.infrastructure.db.repositories.finance_repository import FinanceRepository

        f = await env.seed()
        async with env.session() as holder, env.session() as writer:
            await FinanceRepository(holder).lock_salon(f["salon"])  # held until the holder rolls back
            await writer.execute(text("set local lock_timeout = '500ms'"))
            await writer.execute(text("select id from salons where id = :s for key share"), {"s": f["salon"]})
            # Another finance writer, by contrast, must wait its turn.
            with pytest.raises((DBAPIError, IntegrityError)) as caught:
                await FinanceRepository(writer).lock_salon(f["salon"])
            assert "lock" in str(caught.value).lower()
            await holder.rollback()

    async def test_read_path_indexes_exist(self, env):
        rows = await env.sql(
            "select indexname from pg_indexes where schemaname='public' and indexname in "
            "('idx_booking_payments_salon_captured','idx_bookings_salon_completed')")
        assert len(rows) == 2
