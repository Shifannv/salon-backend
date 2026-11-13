"""Real-PostgreSQL checks of the payment ledger SQL (migration 0029 and PaymentRepository).

Opt-in: set MIGRATION_TEST_DB to a disposable local PostgreSQL admin URL (CREATEDB/CREATEROLE),
e.g. ``postgresql://pgadmin@127.0.0.1:55432/postgres``. Builds a uniquely named database through
the real Alembic chain, and drops it afterwards. These are the tests that prove the trigger and
locking behaviour the unit tests can only describe.
"""

import asyncio
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.migration_policy import PORTABLE_CI_REVISION
from app.infrastructure.db.repositories.payment_repository import PaymentRepository

TEST_DB = os.environ.get("MIGRATION_TEST_DB")
BACKEND = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")
D = Decimal

# 0038–0040 are prepared-only Mumbai migrations with production-specific review guards
# (they verify Supabase-managed privileges that do not exist on a fresh CI postgres).
# All integration test databases stop at this revision; 0038+ are validated separately.


def _alembic(url: str, *args: str) -> str:
    env = dict(os.environ, DATABASE_URL=url, ENVIRONMENT="test", PYTHONIOENCODING="utf-8",
        SALON_ENV_FILE=str(BACKEND / "tests/no-test-env-file"))
    env.setdefault("ACCOUNT_DELETION_SECRET", "local-test-secret-0123456789abcdef0123456789")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", "migration_policy=portable-ci", *args], cwd=BACKEND, env=env,
        check=False, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


async def _build(database: str, *, revision: str = PORTABLE_CI_REVISION) -> None:
    from alembic.script import ScriptDirectory

    from app.core.migration_policy import validate_migration_target
    validate_migration_target(ScriptDirectory(str(BACKEND / "migrations")), revision,
        make_url(TEST_DB).set(drivername="postgresql+asyncpg").render_as_string(hide_password=False),
        {"migration_policy": "portable-ci"})
    admin_url = make_url(TEST_DB)
    assert admin_url.host in {"localhost", "127.0.0.1", "::1"}
    admin = await asyncpg.connect(admin_url.set(drivername="postgresql").render_as_string(hide_password=False))
    try:
        for role in ("postgres", "anon", "authenticated", "service_role"):
            if not await admin.fetchval("select 1 from pg_roles where rolname=$1", role):
                await admin.execute(f'create role "{role}" nologin')
        await admin.execute(f'create database "{database}"')
    finally:
        await admin.close()
    url = admin_url.set(database=database, drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    conn = await asyncpg.connect(admin_url.set(database=database, drivername="postgresql").render_as_string(hide_password=False))
    try:
        await conn.execute("""
            create schema auth;
            create table auth.users (id uuid primary key, email text, phone text,
                raw_user_meta_data jsonb not null default '{}',
                raw_app_meta_data jsonb not null default '{}');
            create function auth.uid() returns uuid language sql stable as $$
                select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
            create publication supabase_realtime;
        """)
        await conn.execute(await asyncio.to_thread(
            _alembic, url, "upgrade", "0004_service_duration_slot_steps", "--sql"))
        await conn.execute("alter table staff drop column experience")
        await conn.execute(await asyncio.to_thread(
            _alembic, url, "upgrade", "0004_service_duration_slot_steps:0014_repair_cancel_reason", "--sql"))
        await asyncio.to_thread(_alembic, url, "upgrade", revision)
        # Notification writes now store the audience. Only the columns are added: the 0069 index needs
        # notifications.deleted_at, which these older revisions do not have.
        audience_sql = BACKEND / "migrations/sql/0069_notification_audience.sql"
        for statement in audience_sql.read_text(encoding="utf-8").split("\n-- statement --\n"):
            if "ADD COLUMN" in statement:
                await conn.execute(statement)
    finally:
        await conn.close()


async def _drop(database: str) -> None:
    admin_url = make_url(TEST_DB)
    admin = await asyncpg.connect(admin_url.set(drivername="postgresql").render_as_string(hide_password=False))
    try:
        await admin.execute(f'drop database if exists "{database}" with (force)')
    finally:
        await admin.close()


@pytest.fixture(scope="module")
def db_url():
    database = "payment_ledger_" + uuid4().hex
    asyncio.run(_build(database))
    yield make_url(TEST_DB).set(database=database, drivername="postgresql+asyncpg").render_as_string(
        hide_password=False)
    asyncio.run(_drop(database))


class Env:
    def __init__(self, url: str):
        self.engine = create_async_engine(url, connect_args={"statement_cache_size": 0})

    def session(self) -> AsyncSession:
        return AsyncSession(self.engine, expire_on_commit=False)

    async def booking(self, total="500.00", deposit=None) -> dict:
        async with self.session() as s:
            await s.execute(text("set local session_replication_role = replica"))  # fixtures only
            owner, customer = uuid4(), uuid4()
            for uid in (owner, customer):
                await s.execute(text("insert into profiles (id) values (:i)"), {"i": uid})
                await s.execute(text("insert into auth.users (id, email) values (:i, :e)"),
                                {"i": uid, "e": f"{uid}@example.test"})
            salon = (await s.execute(text(
                "insert into salons (name, owner_id, approval_status) values ('S', :o, 'approved') returning id"), {"o": owner})).scalar_one()
            staff = (await s.execute(text(
                "insert into staff (salon_id, name) values (:s, 'T') returning id"), {"s": salon})).scalar_one()
            booking = (await s.execute(text(
                """insert into bookings (salon_id, staff_id, customer_id, customer_name, start_datetime,
                       end_datetime, total_duration_minutes, total_price, deposit_amount)
                   values (:s, :t, :c, 'C', now() + interval '1 day', now() + interval '1 day 1 hour',
                           60, :p, :d) returning id"""),
                {"s": salon, "t": staff, "c": customer, "p": D(total), "d": deposit and D(deposit)})).scalar_one()
            await s.commit()
        return {"id": booking, "salon_id": salon, "customer_id": customer, "owner_id": owner,
                "currency": "INR"}

    async def intent(self, booking, amount, order, *, commission="0", base="online_amount", rate="10") -> str:
        async with self.session() as s:
            repo = PaymentRepository(s)
            pid = await repo.insert_intent(
                booking=booking, actor_id=str(booking["customer_id"]), purpose="full",
                amount=D(amount), commission_amount=D(commission), commission_rate_percent=D(rate),
                commission_base=base, commission_policy_version="t1", provider="cashfree",
                settlement_model="platform_collect", intent_reference="pi_" + uuid4().hex,
                order_ref=order, expires_in_seconds=900)
            await s.commit()
        return pid

    async def capture(self, order, amount, pay=None) -> str:
        pay = pay or "pay_" + uuid4().hex
        async with self.session() as s:
            repo = PaymentRepository(s)
            outcome = await repo.apply_payment_observation(
                provider="cashfree", order_ref=order, payment_ref=pay, status="captured",
                amount=D(amount), currency="INR", instrument="upi", failure_code=None)
            await s.commit()
        return outcome

    async def cash(self, booking, amount) -> None:
        async with self.session() as s:
            await s.execute(text(
                """insert into booking_payments (booking_id, salon_id, channel, purpose, method, amount,
                       status, intent_reference, captured_at, settlement_model)
                   values (:b, :s, 'manual', 'full', 'cash', :a, 'captured', :r, now(), 'offline')"""),
                {"b": booking["id"], "s": booking["salon_id"], "a": D(amount), "r": "manual:" + uuid4().hex})
            await s.commit()

    async def one(self, sql: str, **params):
        async with self.session() as s:
            return (await s.execute(text(sql), params)).mappings().one()

    async def booking_row(self, booking):
        return await self.one(
            "select payment_status::text as st, paid_amount, refunded_amount from bookings where id=:i",
            i=booking["id"])


@pytest.fixture
def env(db_url):
    e = Env(db_url)
    yield e
    asyncio.run(e.engine.dispose())


async def test_0029_statements_are_idempotent_and_reapply_cleanly(db_url, env):
    import importlib.util
    from unittest.mock import patch

    spec = importlib.util.spec_from_file_location("m0029", BACKEND / "migrations/versions/0029_payment_monetary_policy.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    statements: list[str] = []
    with patch.object(module.op, "execute", side_effect=lambda s: statements.append(str(s))):
        module.upgrade()
    async with env.engine.begin() as conn:
        for _ in range(2):  # a second pass over an already-upgraded database must succeed
            for statement in statements:
                await conn.exec_driver_sql(statement.replace("%", "%%"))
    row = await env.one("select count(*) as n from information_schema.columns where table_name='booking_payments' and column_name in ('commission_rate_percent','commission_base','platform_commission_amount','commission_policy_version','provider_fee_amount','provider_tax_amount','overcollected_amount')")
    assert row["n"] == 7


async def test_overcollection_is_recorded_not_rolled_back_and_booking_is_not_paid_twice(env):
    booking = await env.booking("500.00")
    await env.cash(booking, "500.00")
    assert (await env.booking_row(booking))["st"] == "paid"
    pid = await env.intent(booking, "500.00", "o_over_1", commission="50.00")
    assert await env.capture("o_over_1", "500.00") == "overcollected"
    row = await env.one("select status, overcollected_amount, payment_ref from booking_payments where id=:i", i=pid)
    assert row["status"] == "captured" and row["overcollected_amount"] == D("500.00")
    paid = await env.booking_row(booking)
    assert paid["st"] == "paid" and paid["paid_amount"] == D("500.00")  # never 1000
    anomaly = await env.one("select kind, amount from payment_anomalies where payment_id=:i", i=pid)
    assert anomaly["kind"] == "overcollection" and anomaly["amount"] == D("500.00")
    # the loop cannot re-fail: the row left the open set
    assert await env.capture("o_over_1", "500.00") == "ignored"


async def test_excess_refund_via_refund_rows_leaves_booking_paid(env):
    booking = await env.booking("500.00")
    await env.cash(booking, "500.00")
    pid = await env.intent(booking, "500.00", "o_over_2")
    await env.capture("o_over_2", "500.00")
    async with env.session() as s:
        repo = PaymentRepository(s)
        payment = await repo.get_payment(str(booking["id"]), pid)
        # more than the excess cannot be refunded as an excess refund
        with pytest.raises(DBAPIError, match="refund_exceeds_payment"):
            await repo.insert_refund(payment=payment, actor_id=str(booking["owner_id"]), amount=D("500.01"),
                                     reason=None, idempotency_key="k-excess-1", applies_to_excess=True)
        await s.rollback()
    async with env.session() as s:
        repo = PaymentRepository(s)
        payment = await repo.get_payment(str(booking["id"]), pid)
        rid = await repo.insert_refund(payment=payment, actor_id=str(booking["owner_id"]), amount=D("500.00"),
                                       reason="excess", idempotency_key="k-excess-2", applies_to_excess=True)
        await repo.update_refund(rid, "rfx", "processed", None)
        await s.commit()
    paid = await env.booking_row(booking)
    assert paid["st"] == "paid" and paid["paid_amount"] == D("500.00") and paid["refunded_amount"] == D("0.00")
    status = await env.one("select status from booking_payments where id=:i", i=pid)
    assert status["status"] == "refunded"
    # a regular refund on a fully-excess payment is impossible: nothing was owed through it
    async with env.session() as s:
        repo = PaymentRepository(s)
        payment = await repo.get_payment(str(booking["id"]), pid)
        totals = await repo.refund_totals(pid)
        assert totals["excess"] == D("500.00") and totals["regular"] == D("0.00")
        with pytest.raises(DBAPIError, match="refund_exceeds_payment"):
            await repo.insert_refund(payment=payment, actor_id=str(booking["owner_id"]), amount=D("1.00"),
                                     reason=None, idempotency_key="k-regular-1")
        await s.rollback()


async def test_partial_online_deposit_then_cash_balance_then_extra_capture(env):
    booking = await env.booking("1000.00", deposit="300.00")
    await env.intent(booking, "300.00", "o_dep")
    assert await env.capture("o_dep", "300.00", "pd" + uuid4().hex) == "applied"
    row = await env.booking_row(booking)
    assert row["st"] == "unpaid" and row["paid_amount"] == D("300.00")
    await env.cash(booking, "700.00")
    assert (await env.booking_row(booking))["st"] == "paid"
    pid = await env.intent(booking, "300.00", "o_dep2")  # a late second online payment
    assert await env.capture("o_dep2", "300.00", "pd2" + uuid4().hex) == "overcollected"
    assert (await env.booking_row(booking))["paid_amount"] == D("1000.00")
    assert (await env.one("select overcollected_amount as x from booking_payments where id=:i", i=pid))["x"] == D("300.00")


async def test_cash_and_online_capture_race_serialises_on_the_booking_lock(env):
    booking = await env.booking("500.00")
    pid = await env.intent(booking, "500.00", "o_race")
    cash_session = env.session()
    await cash_session.execute(text(
        """insert into booking_payments (booking_id, salon_id, channel, purpose, method, amount,
               status, intent_reference, captured_at, settlement_model)
           values (:b, :s, 'manual', 'full', 'cash', 500, 'captured', :r, now(), 'offline')"""),
        {"b": booking["id"], "s": booking["salon_id"], "r": "manual:" + uuid4().hex})
    # the cash transaction holds the booking lock (the recompute trigger ran `for update`)
    online = asyncio.create_task(env.capture("o_race", "500.00", "pr" + uuid4().hex))
    await asyncio.sleep(0.5)
    assert not online.done()  # blocked behind the cash receipt, not racing it
    await cash_session.commit()
    await cash_session.close()
    assert await asyncio.wait_for(online, 10) == "overcollected"
    paid = await env.booking_row(booking)
    assert paid["st"] == "paid" and paid["paid_amount"] == D("500.00")
    assert (await env.one("select overcollected_amount as x from booking_payments where id=:i", i=pid))["x"] == D("500.00")


async def test_online_first_then_cash_receipt_is_refused_by_the_database(env):
    booking = await env.booking("500.00")
    await env.intent(booking, "500.00", "o_first")
    assert await env.capture("o_first", "500.00") == "applied"
    with pytest.raises(DBAPIError, match="payment_overcollection"):
        await env.cash(booking, "500.00")


async def test_commission_snapshot_is_immutable_and_reversal_is_bounded(env):
    booking = await env.booking("1000.00")
    pid = await env.intent(booking, "1000.00", "o_comm", commission="100.00", base="booking_total", rate="10")
    row = await env.one(
        "select commission_rate_percent r, commission_base b, platform_commission_amount a, "
        "commission_policy_version v, provider_fee_amount f, provider_tax_amount t from booking_payments where id=:i", i=pid)
    assert (row["r"], row["b"], row["a"], row["v"]) == (D("10.0000"), "booking_total", D("100.00"), "t1")
    assert row["f"] is None and row["t"] is None  # provider costs are separate and unset
    for column, value in (("platform_commission_amount", "1.00"), ("commission_rate_percent", "5"),
                          ("commission_base", "'online_amount'"), ("commission_policy_version", "'x'")):
        async with env.session() as s:
            with pytest.raises(DBAPIError, match="commission_snapshot_is_immutable"):
                await s.execute(text(f"update booking_payments set {column} = {value} where id = :i"), {"i": pid})
            await s.rollback()
    await env.capture("o_comm", "1000.00")
    async with env.session() as s:
        repo = PaymentRepository(s)
        assert await repo.commission_allocated(str(booking["id"])) == D("100.00")
        payment = await repo.get_payment(str(booking["id"]), pid)
        r1 = await repo.insert_refund(payment=payment, actor_id=str(booking["owner_id"]), amount=D("250.00"),
                                      reason=None, idempotency_key="k-c-1", commission_reversal=D("25.00"))
        await repo.update_refund(r1, "r1", "processed", None)
        await s.commit()
    async with env.session() as s:
        repo = PaymentRepository(s)
        payment = await repo.get_payment(str(booking["id"]), pid)
        with pytest.raises(DBAPIError, match="commission_reversal_exceeds_snapshot"):
            await repo.insert_refund(payment=payment, actor_id=str(booking["owner_id"]), amount=D("750.00"),
                                     reason=None, idempotency_key="k-c-2", commission_reversal=D("75.01"))
        await s.rollback()
    async with env.session() as s:
        totals = await PaymentRepository(s).refund_totals(pid)
    assert totals == {"regular": D("250.00"), "excess": D("0"), "reversed": D("25.00")}


async def test_earnings_use_the_snapshot_and_reversals(env):
    booking = await env.booking("1000.00")
    pid = await env.intent(booking, "1000.00", "o_earn", commission="100.00", base="online_amount", rate="10")
    await env.capture("o_earn", "1000.00")
    async with env.session() as s:
        repo = PaymentRepository(s)
        payment = await repo.get_payment(str(booking["id"]), pid)
        rid = await repo.insert_refund(payment=payment, actor_id=str(booking["owner_id"]), amount=D("400.00"),
                                       reason=None, idempotency_key="k-e-1", commission_reversal=D("40.00"))
        await repo.update_refund(rid, "re1", "processed", None)
        await s.commit()
    async with env.session() as s:
        totals = await PaymentRepository(s).earnings(str(booking["salon_id"]))
    assert totals["online_collected"] == D("1000.00") and totals["platform_fees"] == D("100.00")
    assert totals["online_refunded"] == D("400.00") and totals["commission_reversed"] == D("40.00")
    paid = await env.booking_row(booking)
    assert paid["paid_amount"] == D("1000.00") and paid["refunded_amount"] == D("400.00")


async def test_vendor_registration_state_machine_and_audit(env):
    booking = await env.booking("100.00")
    salon = str(booking["salon_id"])
    owner = str(booking["owner_id"])
    async with env.session() as s:
        repo = PaymentRepository(s)
        first = await repo.begin_registration(salon, "cashfree", owner, lambda g: f"sv{g}")
        assert first["generation"] == 1 and first["previous_status"] is None
        again = await repo.begin_registration(salon, "cashfree", owner, lambda g: f"sv{g}")
        assert again["vendor_ref"] == first["vendor_ref"]  # pending: retried under the same id
        await repo.set_account_result(salon, "cashfree", "active", [], owner)
        redo = await repo.begin_registration(salon, "cashfree", owner, lambda g: f"sv{g}")
        assert redo["generation"] == 2 and redo["previous_status"] == "active"
        account = await repo.get_provider_account(salon, "cashfree")
        assert account["onboarding_status"] == "pending"  # must pass KYC again before payments
        assert await repo.apply_account_update("cashfree", redo["vendor_ref"], "active") == "applied"
        assert await repo.apply_account_update("cashfree", redo["vendor_ref"], "active") == "ignored"
        await s.commit()
    audit = await env.one(
        "select count(*) n, count(*) filter (where action='re_registered') r, "
        "count(*) filter (where action='status_changed') c from payment_provider_account_audit where salon_id=:s", s=booking["salon_id"])
    assert (audit["n"], audit["r"], audit["c"]) == (3, 1, 1)
