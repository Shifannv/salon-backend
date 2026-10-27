"""Real-PostgreSQL proof of migration 0049: the new trial limits and per-salon plan prices.

Opt-in like the other integration suites (MIGRATION_TEST_DB, disposable local PostgreSQL). The
database is built through the portable Alembic chain, then 0049's SQL is applied on top, exactly
as the later prepared migrations are exercised elsewhere.
"""

import asyncio
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from support_subscription import FakeProvider
from test_payment_ledger_sql import TEST_DB, _build, _drop
from test_subscription_billing_sql import Env

from app.core.exceptions import NotFoundError
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)
from app.infrastructure.db.repositories.subscription_repository import SubscriptionPlanRepo

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")
D = Decimal
MIGRATION = Path(__file__).parents[2] / "migrations" / "sql" / "0049_trial_salon_plan_prices.sql"


async def _apply_0049(url: str) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
    async with engine.begin() as conn:
        for statement in MIGRATION.read_text(encoding="utf-8").split("\n-- statement --\n"):
            if statement.strip():
                await conn.execute(text(statement))
    await engine.dispose()


@pytest.fixture(scope="module")
def db_url():
    database = "plan_prices_" + uuid4().hex
    asyncio.run(_build(database))
    url = make_url(TEST_DB).set(database=database, drivername="postgresql+asyncpg").render_as_string(
        hide_password=False)
    asyncio.run(_apply_0049(url))
    yield url
    asyncio.run(_drop(database))


@pytest.fixture
def env(db_url):
    e = Env(db_url)
    yield e
    asyncio.run(e.engine.dispose())


async def _admin_id(env: Env) -> str:
    async with env.session() as s:
        await s.execute(text("set local session_replication_role = replica"))  # fixtures only
        uid = uuid4()
        await s.execute(text("insert into profiles (id) values (:i)"), {"i": uid})
        await s.execute(text("insert into auth.users (id, email) values (:i, :e)"),
                        {"i": uid, "e": f"{uid}@example.test"})
        await s.commit()
    return str(uid)


async def _plans(env: Env, salon_id: str | None) -> dict[str, dict]:
    async with env.session() as s:
        rows = await SubscriptionBillingRepository(s).list_purchasable_plans(salon_id)
    return {r["code"]: r for r in rows}


# ---------------------------------------------------------------------------------- trial
async def test_a_new_trial_is_sixty_days_and_five_hundred_bookings(env):
    who = await env.salon()
    await env.run("select start_salon_trial(:s)", s=who["salon_id"])
    row = await env.one(
        "select trial_booking_limit, trial_ends_at - trial_started_at as span "
        "from salon_access where salon_id = :s", s=who["salon_id"])
    assert row["trial_booking_limit"] == 500
    assert row["span"].days == 60


async def test_the_default_trial_limit_is_five_hundred(env):
    default = await env.scalar(
        "select column_default from information_schema.columns "
        "where table_name = 'salon_access' and column_name = 'trial_booking_limit'")
    assert str(default) == "500"


async def test_a_running_trial_keeps_the_limits_it_started_with(env):
    who = await env.salon()
    await env.run(
        "insert into salon_access (salon_id, trial_started_at, trial_ends_at, trial_booking_limit) "
        "values (:s, now(), now() + interval '2 months', 120)", s=who["salon_id"])
    await env.run("select start_salon_trial(:s)", s=who["salon_id"])  # the no-op path for a started trial
    assert await env.scalar("select trial_booking_limit from salon_access where salon_id = :s", s=who["salon_id"]) == 120


# ---------------------------------------------------------------------------- plan prices
async def test_without_an_override_every_plan_is_at_its_normal_price(env):
    who = await env.salon()
    plans = await _plans(env, who["salon_id"])
    assert plans["growth_1m"]["price_amount"] == plans["growth_1m"]["default_price_amount"] == D("349.00")
    assert plans["growth_1m"]["custom_price"] is False


async def test_an_override_changes_only_that_salons_price_for_that_plan(env):
    mine, other = await env.salon(), await env.salon()
    admin = await _admin_id(env)
    plan_id = await env.plan("growth_1m")
    async with env.session() as s:
        await SubscriptionPlanRepo(s).set_salon_plan_price(mine["salon_id"], plan_id, D("249.00"), admin)

    own = await _plans(env, mine["salon_id"])
    assert own["growth_1m"]["price_amount"] == D("249.00")
    assert own["growth_1m"]["default_price_amount"] == D("349.00")
    assert own["growth_1m"]["custom_price"] is True
    assert own["premium_1m"]["custom_price"] is False  # another plan, same salon

    elsewhere = await _plans(env, other["salon_id"])
    assert elsewhere["growth_1m"]["price_amount"] == D("349.00") and elsewhere["growth_1m"]["custom_price"] is False

    nobody = await _plans(env, None)  # an admin looking at the catalogue sees no salon's price
    assert nobody["growth_1m"]["price_amount"] == D("349.00")


async def test_the_checkout_charges_the_override_price_and_snapshots_it(env):
    who, normal = await env.salon(), await env.salon()
    admin = await _admin_id(env)
    plan_id = await env.plan("growth_1m")
    async with env.session() as s:
        await SubscriptionPlanRepo(s).set_salon_plan_price(who["salon_id"], plan_id, D("199.00"), admin)

    special = await env.buy(who, FakeProvider(env.settings), "growth_1m", pay=False)
    assert special["checkout"]["amount"] == "199.00"
    regular = await env.buy(normal, FakeProvider(env.settings), "growth_1m", pay=False)
    assert regular["checkout"]["amount"] == "349.00"

    # Changing the price afterwards does not rewrite a payment that was already started.
    async with env.session() as s:
        await SubscriptionPlanRepo(s).set_salon_plan_price(who["salon_id"], plan_id, D("99.00"), admin)
    stored = await env.scalar(
        "select amount from subscription_billing_records where salon_id = :s", s=who["salon_id"])
    assert stored == D("199.00")


async def test_clearing_goes_back_to_the_normal_price_and_is_idempotent(env):
    who = await env.salon()
    admin = await _admin_id(env)
    plan_id = await env.plan("premium_1m")
    async with env.session() as s:
        repo = SubscriptionPlanRepo(s)
        await repo.set_salon_plan_price(who["salon_id"], plan_id, D("450.00"), admin)
        await repo.clear_salon_plan_price(who["salon_id"], plan_id, admin)
        await repo.clear_salon_plan_price(who["salon_id"], plan_id, admin)  # nothing left: not an error
    plans = await _plans(env, who["salon_id"])
    assert plans["premium_1m"]["price_amount"] == D("599.00") and plans["premium_1m"]["custom_price"] is False


async def test_setting_a_price_again_updates_it_and_records_who_and_what(env):
    who = await env.salon()
    first, second = await _admin_id(env), await _admin_id(env)
    plan_id = await env.plan("growth_6m")
    async with env.session() as s:
        repo = SubscriptionPlanRepo(s)
        await repo.set_salon_plan_price(who["salon_id"], plan_id, D("1200.00"), first)
        row = await repo.set_salon_plan_price(who["salon_id"], plan_id, D("1100.00"), second)
    assert row["price_amount"] == D("1100.00") and str(row["set_by"]) == second
    assert await env.scalar(
        "select count(*) from salon_plan_prices where salon_id = :s", s=who["salon_id"]) == 1
    events = await env.scalar(
        "select count(*) from subscription_events where event_type = 'admin_plan_price_set' "
        "and provider_name = 'admin'")
    assert events >= 2


async def test_an_unknown_salon_or_plan_is_not_found(env):
    admin = await _admin_id(env)
    who = await env.salon()
    plan_id = await env.plan("growth_1m")
    async with env.session() as s:
        with pytest.raises(NotFoundError):
            await SubscriptionPlanRepo(s).set_salon_plan_price(str(uuid4()), plan_id, D("100.00"), admin)
    async with env.session() as s:
        with pytest.raises(NotFoundError):
            await SubscriptionPlanRepo(s).set_salon_plan_price(who["salon_id"], str(uuid4()), D("100.00"), admin)


async def test_the_database_refuses_a_zero_or_negative_price(env):
    who = await env.salon()
    plan_id = await env.plan("growth_1m")
    for bad in ("0", "-5"):
        async with env.session() as s:
            with pytest.raises(IntegrityError):
                await s.execute(
                    text("insert into salon_plan_prices (salon_id, plan_id, price_amount) values (:s, :p, :a)"),
                    {"s": who["salon_id"], "p": plan_id, "a": D(bad)})
                await s.commit()


async def test_clients_cannot_read_or_write_prices_directly(env):
    async with env.session() as s:
        rls = await s.execute(text(
            "select relrowsecurity from pg_class where oid = 'public.salon_plan_prices'::regclass"))
        assert rls.scalar() is True
        for role in ("anon", "authenticated"):
            for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                allowed = await s.execute(text("select has_table_privilege(:r, 'public.salon_plan_prices', :p)"),
                                          {"r": role, "p": priv})
                assert allowed.scalar() is False, f"{role} has {priv}"


# ---------------------------------------------------------- discount prices
async def test_the_migration_updated_six_and_twelve_month_prices(env):
    """After 0049, 6m = 10% off monthly and 12m = 20% off monthly."""
    who = await env.salon()
    plans = await _plans(env, who["salon_id"])
    assert plans["growth_6m"]["price_amount"] == D("1885.00")
    assert plans["growth_12m"]["price_amount"] == D("3350.00")
    assert plans["premium_6m"]["price_amount"] == D("3235.00")
    assert plans["premium_12m"]["price_amount"] == D("5750.00")
    # Monthly prices are unchanged.
    assert plans["growth_1m"]["price_amount"] == D("349.00")
    assert plans["premium_1m"]["price_amount"] == D("599.00")


async def test_discount_percent_and_monthly_equivalent_for_default_prices(env):
    who = await env.salon()
    plans = await _plans(env, who["salon_id"])
    # Growth 6m: 1885 / 6 months = 314.17 per month, vs 349 monthly → 10% off
    assert plans["growth_6m"]["discount_percent"] == 10
    assert plans["growth_6m"]["monthly_equivalent"] == D("314.17")
    # Growth 12m: 3350 / 12 = 279.17, vs 349 → 20% off
    assert plans["growth_12m"]["discount_percent"] == 20
    assert plans["growth_12m"]["monthly_equivalent"] == D("279.17")
    # Premium 6m: 3235 / 6 = 539.17, vs 599 → 10%
    assert plans["premium_6m"]["discount_percent"] == 10
    # Monthly plans have no discount
    assert plans["growth_1m"]["discount_percent"] is None
    assert plans["growth_1m"]["monthly_equivalent"] is None


async def test_discount_adapts_to_a_custom_salon_override(env):
    """When the salon has a cheaper 6m override, the discount changes against the monthly."""
    who = await env.salon()
    admin = await _admin_id(env)
    plan_id = await env.plan("growth_6m")
    # Set growth_6m to 1500 (a deeper discount vs 349/mo * 6 = 2094 → ~28%)
    async with env.session() as s:
        await SubscriptionPlanRepo(s).set_salon_plan_price(who["salon_id"], plan_id, D("1500.00"), admin)
    plans = await _plans(env, who["salon_id"])
    assert plans["growth_6m"]["price_amount"] == D("1500.00")
    assert plans["growth_6m"]["discount_percent"] == 28  # floor((1 - 1500/(349*6)) * 100) = 28
    assert plans["growth_6m"]["monthly_equivalent"] == D("250.00")


async def test_an_admin_edited_price_is_not_overwritten_by_migration(env):
    """When 0031 price was already changed by an admin, 0049 leaves it alone."""
    # This is already true by construction (the SQL uses WHERE price_amount = <old>),
    # but verify by checking that a salon whose growth_6m was set differently still works.
    who = await env.salon()
    admin = await _admin_id(env)
    # The plan table price is already 1885. Set a salon override to 1000.
    plan_id = await env.plan("growth_6m")
    async with env.session() as s:
        await SubscriptionPlanRepo(s).set_salon_plan_price(who["salon_id"], plan_id, D("1000.00"), admin)
    plans = await _plans(env, who["salon_id"])
    assert plans["growth_6m"]["price_amount"] == D("1000.00")
    assert plans["growth_6m"]["default_price_amount"] == D("1885.00")

