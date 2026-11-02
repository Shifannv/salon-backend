"""Payment settings (0056) on disposable local PostgreSQL: seed, constraints, guard, salon rates, reads."""

from decimal import Decimal as D
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.infrastructure.db.repositories.payment_settings_repository import PaymentSettingsRepository
from app.infrastructure.db.repositories.payments.intents import IntentMixin
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SQL_FILE = Path(__file__).parents[2] / "migrations/sql/0056_platform_payment_settings.sql"


@pytest.fixture(scope="module")
def settings_db(changes_db):  # noqa: F811
    import asyncio

    async def install():
        env = SafetyEnv(changes_db)
        try:
            async with env.session() as session:
                for statement in SQL_FILE.read_text(encoding="utf-8").split("\n-- statement --\n"):
                    if statement.strip():
                        await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()

    asyncio.run(install())
    return changes_db


@pytest.fixture
async def env(settings_db):
    environment = SafetyEnv(settings_db)
    yield environment
    await environment.engine.dispose()


class _Reader(IntentMixin):
    def __init__(self, session):
        self.session = session


async def _reset(env):
    async with env.session() as session:
        await session.execute(text("delete from salon_commission_overrides"))
        await session.execute(text("alter table platform_payment_settings disable trigger platform_payment_settings_guard"))
        await session.execute(text(
            "update platform_payment_settings set commission_rate_percent = null, commission_base = null, "
            "min_payout_paise = 10000, policy_version = 1"))
        await session.execute(text("alter table platform_payment_settings enable trigger platform_payment_settings_guard"))
        await session.commit()


async def test_the_row_is_seeded_with_no_commission_and_the_default_minimum(env):
    await _reset(env)
    async with env.session() as session:
        row = await PaymentSettingsRepository(session).get_settings()
    assert row["commission_rate_percent"] is None and row["commission_base"] is None
    assert row["min_payout_paise"] == 10_000 and row["policy_version"] == 1


async def test_there_can_only_be_one_settings_row(env):
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text("insert into platform_payment_settings (singleton) values (true)"))
        await session.rollback()
        with pytest.raises(IntegrityError):
            await session.execute(text("insert into platform_payment_settings (singleton) values (false)"))


@pytest.mark.parametrize(
    "set_clause",
    [
        "commission_rate_percent = 100.01",
        "commission_rate_percent = -0.01",
        "commission_base = 'everything'",
        "min_payout_paise = 99",
        "min_payout_paise = 100000001",
    ],
)
async def test_bad_values_are_refused_by_the_database(env, set_clause):
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text(f"update platform_payment_settings set {set_clause}"))


async def test_a_rate_without_a_base_or_a_base_without_a_rate_is_refused(env):
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text("update platform_payment_settings set commission_rate_percent = 10, commission_base = null"))
        await session.rollback()
        with pytest.raises(IntegrityError):
            await session.execute(text("update platform_payment_settings set commission_rate_percent = null, commission_base = 'online_amount'"))


async def test_a_change_of_rate_or_base_is_a_new_policy_version_but_the_minimum_is_not(env):
    await _reset(env)
    admin = (await env.seed())["owner"]  # any real profile id will do for updated_by
    async with env.session() as session:
        repo = PaymentSettingsRepository(session)
        first = await repo.update_settings(D("10"), "online_amount", 10_000, admin)
        second = await repo.update_settings(D("10"), "online_amount", 25_000, admin)
        third = await repo.update_settings(D("12.5"), "online_amount", 25_000, admin)
        fourth = await repo.update_settings(D("12.5"), "booking_total", 25_000, admin)
    assert (first["policy_version"], second["policy_version"], third["policy_version"], fourth["policy_version"]) == (2, 2, 3, 4)
    assert second["min_payout_paise"] == 25_000 and third["commission_rate_percent"] == D("12.50")


async def test_the_settings_row_is_never_deleted_or_truncated(env):
    async with env.session() as session:
        with pytest.raises(DBAPIError, match="payment_settings_are_never_deleted"):
            await session.execute(text("delete from platform_payment_settings"))
        await session.rollback()
        with pytest.raises(DBAPIError, match="payment_settings_are_never_deleted"):
            await session.execute(text("truncate platform_payment_settings"))


async def test_a_salon_rate_is_read_next_to_the_platform_rate(env):
    await _reset(env)
    f = await env.seed()
    other = await env.seed()
    actor = f["owner"]
    async with env.session() as session:
        repo = PaymentSettingsRepository(session)
        await repo.update_settings(D("10"), "online_amount", 10_000, actor)
        await repo.set_override(f["salon"], D("4"), "launch deal", actor)
        mine = await _Reader(session).commission_inputs(f["salon"])
        theirs = await _Reader(session).commission_inputs(other["salon"])
        assert await repo.get_override(f["salon"]) == {
            "commission_rate_percent": D("4.00"), "note": "launch deal",
            "updated_at": (await repo.get_override(f["salon"]))["updated_at"],
        }
        await repo.set_override(f["salon"], D("0"), None, actor)  # zero is a real rate
        zero = await _Reader(session).commission_inputs(f["salon"])
        await repo.clear_override(f["salon"])
        cleared = await _Reader(session).commission_inputs(f["salon"])
    assert (mine["salon_rate"], mine["platform_rate"], mine["platform_base"], mine["policy_version"]) == (
        D("4.00"), D("10.00"), "online_amount", 2)
    assert theirs["salon_rate"] is None and theirs["platform_rate"] == D("10.00")
    assert zero["salon_rate"] == D("0.00") and cleared["salon_rate"] is None


async def test_a_salon_rate_is_bounded_and_goes_with_the_salon(env):
    f = await env.seed()
    async with env.session() as session:
        for bad in ("100.01", "-1"):
            with pytest.raises(IntegrityError):
                await session.execute(text(
                    "insert into salon_commission_overrides (salon_id, commission_rate_percent) "
                    f"values (cast(:s as uuid), {bad})"), {"s": f["salon"]})
            await session.rollback()
        with pytest.raises(IntegrityError):  # no such salon
            await session.execute(text(
                "insert into salon_commission_overrides (salon_id, commission_rate_percent) "
                "values (gen_random_uuid(), 5)"))
        await session.rollback()
        await PaymentSettingsRepository(session).set_override(f["salon"], D("5"), None, f["owner"])
        await session.rollback()
    async with env.session() as session:
        rule = (await session.execute(text(
            "select confdeltype from pg_constraint where conrelid = 'salon_commission_overrides'::regclass and contype = 'f' "
            "and confrelid = 'salons'::regclass"))).scalar_one()
    assert rule in ("c", b"c")  # ON DELETE CASCADE: a salon takes its rate with it


async def test_public_roles_cannot_touch_the_settings(env):
    async with env.session() as session:
        for role in ("anon", "authenticated"):
            for table in ("platform_payment_settings", "salon_commission_overrides"):
                allowed = (await session.execute(text(
                    f"select has_table_privilege('{role}', 'public.{table}', 'SELECT')"))).scalar_one()
                assert allowed is False, (role, table)
        rls = (await session.execute(text(
            "select relname, relrowsecurity from pg_class where relname in "
            "('platform_payment_settings', 'salon_commission_overrides')"))).all()
    assert all(enabled for _, enabled in rls) and len(rls) == 2
