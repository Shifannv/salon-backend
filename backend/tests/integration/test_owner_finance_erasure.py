"""Account erasure vs the owner cash book (0051) on the real prepared schema (0038..0051).

Free text goes, money records stay, and erasure keeps working. The database is the portable chain
plus every prepared sidecar, exactly as test_prepared_erasure_sql builds it, so the booking-audit
privacy checks and the verified-deletion-request gate are the real ones.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_owner_finance_sql import digest
from tests.integration.test_payment_ledger_sql import TEST_DB, _build, _drop

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

NAME = "Hafis-the-barber"
LAST_PREPARED = 51

# What erasure does with every text column of the cash book. Reviewed with the migration: a new
# column must be added here deliberately.
FINANCE_COLUMN_TREATMENT = {
    "salon_expenses.entry_type": "code", "salon_expenses.category": "code",
    "salon_expenses.payment_method": "code", "salon_expenses.note": "cleared-on-owner-erasure",
    "salon_expenses.idempotency_key": "client-key", "salon_expenses.request_hash": "digest",
    "salon_cash_adjustments.direction": "code", "salon_cash_adjustments.reason": "replaced-on-owner-erasure",
    "salon_cash_adjustments.idempotency_key": "client-key", "salon_cash_adjustments.request_hash": "digest",
    "salon_day_closes.difference_reason": "replaced-on-owner-erasure",
    "salon_day_closes.idempotency_key": "client-key", "salon_day_closes.request_hash": "digest",
}


@pytest.fixture(scope="module")
def prepared_db():
    name = "finance_erasure_" + uuid4().hex
    asyncio.run(_build(name))
    url = make_url(TEST_DB).set(database=name, drivername="postgresql+asyncpg").render_as_string(hide_password=False)

    async def install():
        environment = SafetyEnv(url)
        try:
            # Same managed-role prerequisite the prepared erasure suite uses, confined to this database.
            await environment.sql("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role")
            for number in range(38, LAST_PREPARED + 1):
                files = list((Path(__file__).parents[2] / "migrations/sql").glob(f"{number:04d}_*.sql"))
                assert len(files) == 1, number
                async with environment.session() as session:
                    for statement in files[0].read_text(encoding="utf-8").split("\n-- statement --\n"):
                        if statement.strip():
                            await session.execute(text(statement))
                    await session.commit()
        finally:
            await environment.engine.dispose()

    try:
        asyncio.run(install())
        yield url
    finally:
        asyncio.run(_drop(name))


@pytest.fixture
async def env(prepared_db):
    environment = SafetyEnv(prepared_db)
    yield environment
    await environment.engine.dispose()


async def seed_cash_book(env, f):
    for prefix, sql, free_text in (
        ("e", """insert into salon_expenses(salon_id, entry_type, category, amount_paise, payment_method,
                occurred_at, note, created_by, idempotency_key, request_hash)
            values(:s, 'expense', 'salary_advance', 5000, 'cash', now(), :t, :by, :k, :h)""", "advance to " + NAME),
        ("a", """insert into salon_cash_adjustments(salon_id, direction, amount_paise, reason, occurred_at,
                created_by, idempotency_key, request_hash) values(:s, 'out', 2500, :t, now(), :by, :k, :h)""",
         "gave " + NAME + " change"),
        ("c", """insert into salon_day_closes(salon_id, local_date, revision, opening_cash_paise,
                expected_cash_paise, actual_cash_paise, difference_reason, created_by, idempotency_key, request_hash)
            values(:s, current_date, 1, 0, 1000, 900, :t, :by, :k, :h)""", NAME + " took 100"),
    ):
        key = prefix + "-" + uuid4().hex
        await env.sql(sql, s=f["salon"], t=free_text, by=f["owner"], k=key, h=digest(key))


async def snapshot(env, salon):
    return {
        "expenses": await env.sql("select amount_paise, category, payment_method, note, created_by from salon_expenses where salon_id = :s", s=salon),
        "adjustments": await env.sql("select amount_paise, direction, reason, created_by from salon_cash_adjustments where salon_id = :s", s=salon),
        "closes": await env.sql("select actual_cash_paise, expected_cash_paise, difference_paise, difference_reason, created_by from salon_day_closes where salon_id = :s", s=salon),
    }


async def erase(env, user_id, role):
    """The real erasure, behind the same gate as production: a verified 'processing' request."""
    await env.sql("insert into account_deletion_requests(user_id, role, status) values(:u, :r, 'processing')",
                  u=user_id, r=role)
    async with env.session() as session:
        await SQLAccountDeletionRepository(session).erase_database(user_id, role, [])


async def test_the_cash_book_text_columns_are_all_classified_for_erasure(env):
    rows = await env.sql(
        """select table_name || '.' || column_name as col from information_schema.columns
           where table_schema = 'public'
             and table_name in ('salon_expenses','salon_cash_adjustments','salon_day_closes')
             and data_type in ('text', 'character varying', 'jsonb', 'json', 'ARRAY')""")
    assert {r["col"] for r in rows} == set(FINANCE_COLUMN_TREATMENT)


async def test_owner_erasure_clears_free_text_and_keeps_every_money_record(env):
    f = await env.seed()
    await seed_cash_book(env, f)
    before = await snapshot(env, f["salon"])
    assert NAME in str(before)

    await erase(env, f["owner"], "owner")

    after = await snapshot(env, f["salon"])
    assert NAME not in str(after)
    assert after["expenses"] == [{**before["expenses"][0], "note": None, "created_by": None}]
    assert after["adjustments"] == [{**before["adjustments"][0], "reason": "Removed", "created_by": None}]
    assert after["closes"] == [{**before["closes"][0], "difference_reason": "Removed", "created_by": None}]
    assert after["closes"][0]["difference_paise"] == -100  # database-computed, untouched
    assert (await env.sql("select count(*) as n from profiles where id = :i", i=f["owner"]))[0]["n"] == 0


async def test_the_scrub_can_run_again_without_error(env):
    f = await env.seed()
    await seed_cash_book(env, f)
    async with env.session() as session:
        repo = SQLAccountDeletionRepository(session)
        await repo._scrub_owner_finance({"uid": f["owner"]})
        await repo._scrub_owner_finance({"uid": f["owner"]})
        await session.commit()
    assert NAME not in str(await snapshot(env, f["salon"]))


async def test_erasing_a_customer_leaves_the_cash_book_and_other_salons_alone(env):
    f, other = await env.seed(), await env.seed()
    await seed_cash_book(env, f)
    await seed_cash_book(env, other)
    key = "x-" + uuid4().hex
    await env.sql(
        """insert into salon_expenses(salon_id, entry_type, category, amount_paise, payment_method, occurred_at,
             note, created_by, idempotency_key, request_hash)
           values(:s, 'expense', 'other', 700, 'cash', now(), 'kept', :by, :k, :h)""",
        s=f["salon"], by=f["customer"], k=key, h=digest(key))

    await erase(env, f["customer"], "customer")

    mine = await env.sql("select note, created_by, amount_paise from salon_expenses where salon_id = :s and amount_paise = 700", s=f["salon"])
    assert mine == [{"note": "kept", "created_by": None, "amount_paise": 700}]  # the note is the owner's, not the customer's
    await erase(env, f["owner"], "owner")
    assert NAME in str(await snapshot(env, other["salon"]))  # another salon's cash book is untouched


async def test_erasure_still_works_when_the_cash_book_does_not_exist_yet(env):
    f = await env.seed()
    async with env.session() as session:
        await session.execute(text("alter table salon_expenses rename to salon_expenses_hidden"))
        repo = SQLAccountDeletionRepository(session)
        await repo._scrub_owner_finance({"uid": f["owner"]})  # skipped, not an error
        await session.rollback()
