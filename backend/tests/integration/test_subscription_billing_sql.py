"""Real-PostgreSQL proof of subscription billing (migrations 0030/0031 + repository + use cases).

Opt-in like the other integration suites: set MIGRATION_TEST_DB to a disposable local PostgreSQL
admin URL (``postgresql://pgadmin@127.0.0.1:55433/postgres``). A uniquely named database is built
through the real Alembic chain and dropped afterwards. These are the tests that prove the
atomic, idempotent, overlap-free activation the unit tests can only describe.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from support_subscription import (
    FakeProvider,
    owner,
    resolver_for,
    sub_settings,
    webhook,
)
from test_payment_ledger_sql import _TEST_HEAD, BACKEND, TEST_DB, _alembic, _build, _drop

from app.application.use_cases.subscription_billing import (
    SubscriptionBillingUseCases,
    SubscriptionReconciler,
    SubscriptionWebhookHandler,
    subscription_event_to_json,
)
from app.core.exceptions import ConflictError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")
D = Decimal
GRACE = 3


@pytest.fixture(scope="module")
def db_url():
    database = "sub_billing_" + uuid4().hex
    asyncio.run(_build(database))
    yield make_url(TEST_DB).set(database=database, drivername="postgresql+asyncpg").render_as_string(
        hide_password=False)
    asyncio.run(_drop(database))


class Env:
    def __init__(self, url: str):
        self.engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
        self.settings = sub_settings(subscription_grace_days=GRACE)

    def session(self) -> AsyncSession:
        return AsyncSession(self.engine, expire_on_commit=False)

    async def run(self, sql: str, **params):
        async with self.session() as s:
            result = await s.execute(text(sql), params)
            await s.commit()
            return result

    async def one(self, sql: str, **params) -> dict:
        async with self.session() as s:
            return dict((await s.execute(text(sql), params)).mappings().one())

    async def scalar(self, sql: str, **params):
        async with self.session() as s:
            return (await s.execute(text(sql), params)).scalar()

    async def salon(self) -> dict:
        async with self.session() as s:
            await s.execute(text("set local session_replication_role = replica"))  # fixtures only
            uid = uuid4()
            await s.execute(text("insert into profiles (id) values (:i)"), {"i": uid})
            await s.execute(text("insert into auth.users (id, email) values (:i, :e)"),
                            {"i": uid, "e": f"{uid}@example.test"})
            salon = (await s.execute(text(
                "insert into salons (name, owner_id, approval_status, profile_completed) "
                "values ('S', :o, 'approved', true) returning id"), {"o": uid})).scalar_one()
            await s.commit()
        return {"owner_id": str(uid), "salon_id": str(salon)}

    async def sweep(self) -> int:
        async with self.session() as s:
            n = (await s.execute(text("select sweep_lapsed_subscriptions()"))).scalar()
            await s.commit()
            return n

    async def backdate(self, billing_id: str, *, expired: bool = False) -> None:
        async with self.session() as s:
            await s.execute(text("set local session_replication_role = replica"))  # fixtures only
            await s.execute(text(
                "update subscription_billing_records set updated_at = now() - interval '1 hour'"
                + (", expires_at = now() - interval '1 minute'" if expired else "")
                + " where id = :i"), {"i": billing_id})
            await s.commit()

    async def plan(self, code: str) -> str:
        return str(await self.scalar("select id from subscription_plans where code = :c", c=code))

    def usecases(self, session: AsyncSession, provider: FakeProvider) -> SubscriptionBillingUseCases:
        return SubscriptionBillingUseCases(
            SubscriptionBillingRepository(session), resolver_for(provider, self.settings),
            self.settings, PlatformRepository(session))

    async def buy(self, who: dict, provider: FakeProvider, code: str = "growth_1m", *,
                  pay: bool = True) -> dict:
        """checkout -> (provider captures) -> verify, returning the verify state."""
        plan_id = await self.plan(code)
        async with self.session() as s:
            uc = self.usecases(s, provider)
            await uc.repository.set_actor(who["owner_id"])
            body = await uc.checkout(owner(who["owner_id"]), plan_id, "k-" + uuid4().hex)
        if not pay:
            return {"checkout": body}
        provider.pay(body["order_ref"])
        async with self.session() as s:
            uc = self.usecases(s, provider)
            await uc.repository.set_actor(who["owner_id"])
            state = await uc.verify(owner(who["owner_id"]), body["order_ref"])
        return {"checkout": body, "state": state}

    async def subscriptions(self, salon_id: str) -> list[dict]:
        async with self.session() as s:
            rows = (await s.execute(text(
                "select id, status, current_period_start, current_period_end, grace_period_end, "
                "cancelled_at, plan_id from salon_subscriptions where salon_id = :s "
                "order by created_at"), {"s": salon_id})).mappings().all()
            return [dict(r) for r in rows]

    async def active_promotions(self, salon_id: str) -> int:
        return await self.scalar(
            "select count(*) from salon_subscriptions s where s.salon_id = :s and "
            "is_subscription_promotion_active(s.status, s.current_period_start, "
            "s.current_period_end, s.grace_period_end)", s=salon_id)


@pytest.fixture
def env(db_url):
    e = Env(db_url)
    yield e
    asyncio.run(e.engine.dispose())


# ============================================================ migrations / seed
async def test_plans_are_seeded_with_decimal_prices_features_and_unknown_tax(env):
    rows = {r["code"]: r for r in (await _plans(env))}
    expected = {"growth_1m": "349.00", "growth_6m": "1499.00", "growth_12m": "1999.00",
                "premium_1m": "599.00", "premium_6m": "2499.00", "premium_12m": "3499.00"}
    for code, price in expected.items():
        assert str(rows[code]["price_amount"]) == price and rows[code]["currency"] == "INR"
        assert rows[code]["tax_inclusive"] is None
    assert rows["growth_6m"]["billing_interval"] == "semiannual"
    assert set(rows["growth_1m"]["features"]) == {"unlimited_bookings", "split_bill", "daily_ledger"}
    assert rows["premium_1m"]["features"]["monthly_alert_cap"] == 300
    assert rows["premium_12m"]["features"]["rank_boost"] is True


async def _plans(env):
    async with env.session() as s:
        return [dict(r) for r in (await s.execute(text(
            "select code, price_amount, currency, billing_interval, features, tax_inclusive "
            "from subscription_plans"))).mappings().all()]


async def test_reseeding_never_overwrites_an_admin_edited_plan(env):
    import importlib.util
    from unittest.mock import patch

    await env.run("update subscription_plans set price_amount = 400.00 where code = 'growth_1m'")
    spec = importlib.util.spec_from_file_location(
        "m0031", BACKEND / "migrations/versions/0031_seed_subscription_plans.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    statements: list[str] = []
    with patch.object(module.op, "execute", side_effect=lambda s: statements.append(str(s))):
        module.upgrade()
    async with env.engine.begin() as conn:
        for _ in range(2):
            for statement in statements:
                await conn.exec_driver_sql(statement)
    assert str(await env.scalar("select price_amount from subscription_plans where code='growth_1m'")
               ) == "400.00"
    assert await env.scalar("select count(*) from subscription_plans where code like 'growth\\_%'") == 3
    await env.run("update subscription_plans set price_amount = 349.00 where code = 'growth_1m'")


async def test_0030_statements_are_idempotent_and_plan_checks_exist(env):
    import importlib.util
    from unittest.mock import patch

    spec = importlib.util.spec_from_file_location(
        "m0030", BACKEND / "migrations/versions/0030_subscription_billing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    statements: list[str] = []
    with patch.object(module.op, "execute", side_effect=lambda s: statements.append(str(s))):
        module.upgrade()
    async with env.engine.begin() as conn:
        for _ in range(2):
            for statement in statements:
                await conn.exec_driver_sql(statement)
    with pytest.raises(DBAPIError):
        await env.run("update subscription_plans set billing_interval = 'fortnightly' "
                      "where code = 'growth_1m'")
    with pytest.raises(DBAPIError):
        await env.run("update subscription_plans set currency = 'inr' where code = 'growth_1m'")
    with pytest.raises(DBAPIError):
        await env.run("update subscription_plans set price_amount = -1 where code = 'growth_1m'")


async def test_the_browser_roles_cannot_read_or_activate_billing(env):
    who = await env.salon()
    await env.buy(who, FakeProvider(), pay=False)
    async with env.session() as s:
        await s.execute(text("set local role authenticated"))
        with pytest.raises(ProgrammingError):
            await s.execute(text("select * from subscription_billing_records"))
    async with env.session() as s:
        await s.execute(text("set local role anon"))
        with pytest.raises(ProgrammingError):
            await s.execute(text("select apply_subscription_billing_record(gen_random_uuid(), 0)"))
    async with env.session() as s:
        await s.execute(text("set local role authenticated"))
        with pytest.raises(ProgrammingError):
            await s.execute(text("select cancel_salon_subscription_renewal(gen_random_uuid())"))


# =========================================================== activation semantics
async def test_purchase_activates_once_and_duplicate_verification_never_extends(env):
    who, provider = await env.salon(), FakeProvider()
    result = await env.buy(who, provider)
    state = result["state"]
    assert state["verification"] == "started" and state["entitlement_active"] is True
    (sub,) = await env.subscriptions(who["salon_id"])
    end = sub["current_period_end"]
    assert end - sub["current_period_start"] >= timedelta(days=28)
    assert sub["grace_period_end"] - end == timedelta(days=GRACE)
    for _ in range(3):
        async with env.session() as s:
            uc = env.usecases(s, provider)
            again = await uc.verify(owner(who["owner_id"]), result["checkout"]["order_ref"])
        assert again["verification"] == "already_applied"
    (sub2,) = await env.subscriptions(who["salon_id"])
    assert sub2["current_period_end"] == end
    row = await env.one("select status, applied_at, period_end, subscription_id, amount "
                        "from subscription_billing_records where salon_id = :s", s=who["salon_id"])
    assert row["status"] == "paid" and row["applied_at"] is not None and row["period_end"] == end
    assert await env.scalar("select count(*) from subscription_events where "
                            "salon_subscription_id = :i", i=sub["id"]) == 1


async def test_concurrent_applications_extend_exactly_once(env):
    who, provider = await env.salon(), FakeProvider()
    first = await env.buy(who, provider)
    first_end = await env.scalar(
        "select period_end from subscription_billing_records where id = :i",
        i=first["checkout"]["billing_id"])
    second = await env.buy(who, provider, pay=False)
    pay_ref = provider.pay(second["checkout"]["order_ref"])
    billing_id = second["checkout"]["billing_id"]
    async with env.session() as s:
        assert await SubscriptionBillingRepository(s).mark_paid(billing_id, pay_ref)
        await s.commit()

    async def racer():
        async with env.session() as s:
            outcome = await SubscriptionBillingRepository(s).apply(billing_id, GRACE)
            await s.commit()
            return outcome

    outcomes = await asyncio.gather(*(racer() for _ in range(6)))
    assert sorted(outcomes) == ["already_applied"] * 5 + ["renewed"]
    (sub,) = await env.subscriptions(who["salon_id"])
    assert timedelta(days=28) <= sub["current_period_end"] - first_end < timedelta(days=32)


async def test_renewal_extends_from_the_paid_through_date_on_the_same_row(env):
    who, provider = await env.salon(), FakeProvider()
    await env.buy(who, provider)
    (before,) = await env.subscriptions(who["salon_id"])
    second = await env.buy(who, provider)  # same plan, bought while the first period still runs
    assert second["state"]["verification"] == "renewed"
    (after,) = await env.subscriptions(who["salon_id"])  # still ONE row, no overlap
    assert after["id"] == before["id"] and after["current_period_start"] == before["current_period_start"]
    one_month = await env.scalar("select cast(:s as timestamptz) + interval '1 month' = cast(:e as timestamptz)",
                                 s=before["current_period_end"], e=after["current_period_end"])
    assert one_month is True  # exactly one more month, counted from the OLD paid-through date
    assert await env.active_promotions(who["salon_id"]) == 1
    row = await env.one("select period_start from subscription_billing_records where id = :i",
                        i=second["checkout"]["billing_id"])
    assert row["period_start"] == before["current_period_end"]
    # a different plan is refused until the paid period ends (no proration is invented)
    async with env.session() as s:
        with pytest.raises(ConflictError):
            await env.usecases(s, provider).checkout(
                owner(who["owner_id"]), await env.plan("growth_6m"), "k-" + uuid4().hex)


async def test_cancel_keeps_paid_through_access_and_renewing_reuses_the_cancelled_row(env):
    who, provider = await env.salon(), FakeProvider()
    await env.buy(who, provider)
    (before,) = await env.subscriptions(who["salon_id"])
    async with env.session() as s:
        uc = env.usecases(s, provider)
        first = await uc.cancel(owner(who["owner_id"]))
        second = await uc.cancel(owner(who["owner_id"]))
    for state in (first, second):
        assert state["cancelled"] is True and state["entitlement_active"] is True
        assert state["entitlement_state"] == "cancelled_paid_through"
    (cancelled,) = await env.subscriptions(who["salon_id"])
    assert cancelled["status"] == "cancelled" and cancelled["cancelled_at"] is not None
    assert cancelled["current_period_end"] == before["current_period_end"]
    assert await env.active_promotions(who["salon_id"]) == 1
    renewed = await env.buy(who, provider)  # a cancelled-but-paid-through period is renewed in place
    assert renewed["state"]["verification"] == "renewed" and renewed["state"]["cancelled"] is False
    (row,) = await env.subscriptions(who["salon_id"])
    assert row["id"] == before["id"] and row["status"] == "active" and row["cancelled_at"] is None
    assert row["current_period_end"] > before["current_period_end"]
    assert await env.scalar("select count(*) from salon_subscriptions where salon_id = :s and "
                            "status not in ('expired','cancelled','suspended')", s=who["salon_id"]) == 1


async def test_lapse_grace_expiry_and_a_fresh_purchase_afterwards(env):
    who, provider = await env.salon(), FakeProvider()
    await env.buy(who, provider)
    (sub,) = await env.subscriptions(who["salon_id"])
    # period ended 1 day ago, grace (3 days) still open: benefit continues
    await env.run("update salon_subscriptions set current_period_start = now() - interval '31 days', "
                  "current_period_end = now() - interval '1 day', "
                  "grace_period_end = now() + interval '2 days' where id = :i", i=sub["id"])
    assert await env.active_promotions(who["salon_id"]) == 1
    assert await env.sweep() == 1
    assert (await env.subscriptions(who["salon_id"]))[0]["status"] == "past_due"
    assert await env.active_promotions(who["salon_id"]) == 1
    async with env.session() as s:
        state = await env.usecases(s, provider).get_subscription(owner(who["owner_id"]))
    assert state["in_grace"] is True and state["entitlement_active"] is True
    # grace over
    await env.run("update salon_subscriptions set grace_period_end = now() - interval '1 hour' "
                  "where id = :i", i=sub["id"])
    assert await env.active_promotions(who["salon_id"]) == 0
    assert await env.sweep() == 1
    assert (await env.subscriptions(who["salon_id"]))[0]["status"] == "expired"
    assert await env.sweep() == 0  # idempotent
    # history, refunds and cancel are never blocked by the lapse
    async with env.session() as s:
        uc = env.usecases(s, provider)
        assert len(await uc.history(owner(who["owner_id"]), 10, 0)) == 1
        assert (await uc.get_subscription(owner(who["owner_id"])))["entitlement_state"] == "expired"
    renewed = await env.buy(who, provider)
    assert renewed["state"]["verification"] == "started"
    rows = await env.subscriptions(who["salon_id"])
    assert [r["status"] for r in rows] == ["expired", "active"]
    assert rows[1]["current_period_start"] > rows[0]["current_period_end"]
    assert await env.active_promotions(who["salon_id"]) == 1


async def test_a_lapsed_active_row_within_stored_grace_keeps_the_benefit_without_a_sweep(env):
    who, provider = await env.salon(), FakeProvider()
    await env.buy(who, provider)
    await env.run("update salon_subscriptions set current_period_start = now() - interval '31 days', "
                  "current_period_end = now() - interval '1 hour', "
                  "grace_period_end = now() + interval '2 days' where salon_id = :s", s=who["salon_id"])
    assert await env.active_promotions(who["salon_id"]) == 1  # status is still 'active'
    await env.run("update salon_subscriptions set grace_period_end = null where salon_id = :s",
                  s=who["salon_id"])
    assert await env.active_promotions(who["salon_id"]) == 0  # admin-style rows never gain grace


async def test_plan_price_change_after_purchase_does_not_rewrite_history(env):
    who, provider = await env.salon(), FakeProvider()
    result = await env.buy(who, provider, "growth_1m")
    billing_id = result["checkout"]["billing_id"]
    await env.run("update subscription_plans set price_amount = 999.00, "
                  "features = '{\"changed\": true}'::jsonb where code = 'growth_1m'")
    try:
        row = await env.one("select amount, benefits, plan_code from subscription_billing_records "
                            "where id = :i", i=billing_id)
        assert row["amount"] == D("349.00") and "split_bill" in row["benefits"]
        with pytest.raises(DBAPIError, match="snapshot_is_immutable"):
            await env.run("update subscription_billing_records set amount = 1 where id = :i", i=billing_id)
        with pytest.raises(DBAPIError, match="snapshot_is_immutable"):
            await env.run("update subscription_billing_records set benefits = '{}'::jsonb "
                          "where id = :i", i=billing_id)
        with pytest.raises(DBAPIError, match="status_regression"):
            await env.run("update subscription_billing_records set status = 'created' "
                          "where id = :i", i=billing_id)
        with pytest.raises(DBAPIError, match="application_is_immutable"):
            await env.run("update subscription_billing_records set period_end = now() "
                          "where id = :i", i=billing_id)
        again = await env.buy(who, provider, "growth_1m")  # the NEW purchase uses the new price
        assert str(await env.scalar("select amount from subscription_billing_records where id = :i",
                                    i=again["checkout"]["billing_id"])) == "999.00"
    finally:
        await env.run("update subscription_plans set price_amount = 349.00, features = "
                      "'{\"unlimited_bookings\": true, \"split_bill\": true, \"daily_ledger\": true}'"
                      "::jsonb where code = 'growth_1m'")


async def test_one_open_purchase_per_salon_is_enforced_by_the_database(env):
    who, provider = await env.salon(), FakeProvider()
    await env.buy(who, provider, pay=False)
    async with env.session() as s:
        repo = SubscriptionBillingRepository(s)
        with pytest.raises(ConflictError):
            await repo.insert_billing(
                salon_id=who["salon_id"], plan_id=await env.plan("growth_1m"), provider="razorpay",
                receipt="sub_" + uuid4().hex, actor_id=who["owner_id"], ttl_seconds=600)


async def test_provider_references_are_unique_per_provider(env):
    a, c = await env.salon(), await env.salon()
    pa = await env.buy(a, FakeProvider(), pay=False)
    order = pa["checkout"]["order_ref"]
    plan = await env.plan("growth_1m")
    insert = (
        "insert into subscription_billing_records (salon_id, plan_id, plan_code, provider, receipt, "
        "provider_order_ref, amount, currency, billing_interval, expires_at) values (:s, :p, "
        "'growth_1m', :prov, :r, :o, 349, 'INR', 'monthly', now() + interval '1 hour')"
    )
    with pytest.raises(DBAPIError, match="uq_subscription_billing_order"):
        await env.run(insert, s=c["salon_id"], p=plan, prov="razorpay", r="sub_" + uuid4().hex, o=order)
    # the same reference under ANOTHER provider is a different order
    await env.run(insert, s=c["salon_id"], p=plan, prov="otherpay", r="sub_" + uuid4().hex, o=order)


async def test_a_suspended_salon_cannot_start_a_new_checkout(env):
    who, provider = await env.salon(), FakeProvider()
    await env.buy(who, provider)
    await env.run("update salon_subscriptions set status = 'suspended' where salon_id = :s",
                  s=who["salon_id"])
    async with env.session() as s:
        with pytest.raises(ConflictError):
            await env.usecases(s, provider).checkout(
                owner(who["owner_id"]), await env.plan("growth_1m"), "k-" + uuid4().hex)


async def test_a_payment_that_lands_on_a_suspended_or_closed_salon_is_held_and_flagged(env):
    who, provider = await env.salon(), FakeProvider()
    pending = await env.buy(who, provider, pay=False)
    await env.run("insert into salon_subscriptions (salon_id, plan_id, status) values (:s, :p, 'suspended')",
                  s=who["salon_id"], p=await env.plan("growth_1m"))
    provider.pay(pending["checkout"]["order_ref"])
    async with env.session() as s:
        uc = env.usecases(s, provider)
        out = await uc.verify(owner(who["owner_id"]), pending["checkout"]["order_ref"])
    assert out["verification"] == "blocked_suspended" and out["entitlement_active"] is False
    row = await env.one("select status, applied_at from subscription_billing_records where id = :i",
                        i=pending["checkout"]["billing_id"])
    assert row["status"] == "paid" and row["applied_at"] is None  # money recorded, access not granted
    assert await env.scalar("select count(*) from payment_anomalies where kind = 'subscription_blocked' "
                            "and salon_id = :s", s=who["salon_id"]) == 1
    # closed salon (owner removed by account erasure) -> blocked_closed
    closed = await env.salon()
    pending2 = await env.buy(closed, provider, pay=False)
    provider.pay(pending2["checkout"]["order_ref"])
    await env.run("update salons set owner_id = null, is_active = false where id = :s", s=closed["salon_id"])
    async with env.session() as s:
        repo = SubscriptionBillingRepository(s)
        await repo.mark_paid(pending2["checkout"]["billing_id"], "pay_closed_1")
        assert await repo.apply(pending2["checkout"]["billing_id"], GRACE) == "blocked_closed"
        await s.commit()
    assert await env.subscriptions(closed["salon_id"]) == []


async def test_an_amount_mismatch_at_the_provider_never_creates_a_subscription(env):
    who, provider = await env.salon(), FakeProvider()
    pending = await env.buy(who, provider, pay=False)
    provider.pay(pending["checkout"]["order_ref"], amount=D("1.00"))
    async with env.session() as s:
        out = await env.usecases(s, provider).verify(owner(who["owner_id"]), pending["checkout"]["order_ref"])
    assert out["verification"] == "mismatch" and await env.subscriptions(who["salon_id"]) == []
    assert (await env.one("select status from subscription_billing_records where id = :i",
                          i=pending["checkout"]["billing_id"]))["status"] == "created"


# ============================================== webhooks end to end over the real intake
async def test_duplicate_delayed_and_out_of_order_webhooks_never_extend_twice(env):
    from app.application.use_cases.payments import PaymentWebhookUseCases
    from app.infrastructure.db.repositories.payment_repository import PaymentRepository
    from app.infrastructure.payments.resolver import PaymentGatewayResolver

    who, provider = await env.salon(), FakeProvider()
    pending = await env.buy(who, provider, pay=False)
    order, billing = pending["checkout"]["order_ref"], pending["checkout"]["billing_id"]
    pay = provider.pay(order)
    resolver = PaymentGatewayResolver(env.settings, subscription_provider_port=provider)

    async def deliver(event: str, event_id: str, **kw) -> tuple[str, str | None, str | None]:
        body, headers = webhook(event, order=order, payment=pay, amount_paise=34900, event_id=event_id, **kw)
        async with env.session() as s:
            uc = PaymentWebhookUseCases(PaymentRepository(s), resolver, env.settings)
            ack, row_id = await uc.ingest("razorpay", body, headers)
        final = None
        if row_id:
            async with env.session() as s:
                uc = PaymentWebhookUseCases(
                    PaymentRepository(s), resolver, env.settings,
                    SubscriptionWebhookHandler(SubscriptionBillingRepository(s),
                                               resolver_for(provider, env.settings), env.settings))
                final = await uc.process(row_id)
        return ack, row_id, final

    # delayed failure arrives FIRST, then capture, then duplicates and a late failure again
    assert (await deliver("payment.failed", "evt_a"))[2] == "processed"
    assert (await deliver("payment.captured", "evt_b"))[2] == "processed"
    ack, _, _ = await deliver("payment.captured", "evt_b")
    assert ack == "duplicate"
    assert (await deliver("order.paid", "evt_c"))[2] == "processed"
    assert (await deliver("payment.failed", "evt_d"))[2] == "processed"
    (sub,) = await env.subscriptions(who["salon_id"])
    end = sub["current_period_end"]
    assert (await env.one("select status, applied_at is not null as applied from "
                          "subscription_billing_records where id = :i", i=billing)) == {
        "status": "paid", "applied": True}
    assert await env.scalar("select count(*) from payment_webhook_events where "
                            "provider_name = 'razorpay'") >= 4
    # a refund event converges without revoking access
    provider.payments[pay]["refunded"] = D("349.00")
    assert (await deliver("refund.processed", "evt_e", refund="rfnd_9"))[2] == "processed"
    row = await env.one("select status, refunded_amount from subscription_billing_records where id = :i",
                        i=billing)
    assert row["status"] == "refunded" and row["refunded_amount"] == D("349.00")
    (still,) = await env.subscriptions(who["salon_id"])
    assert still["current_period_end"] == end and still["status"] == "active"


async def test_a_forged_signature_stores_nothing_and_both_providers_work_simultaneously(env):
    from test_payment_ledger_sql import Env as LedgerEnv

    from app.application.use_cases.payments import PaymentWebhookUseCases
    from app.core.config import Settings
    from app.core.exceptions import InvalidWebhookSignatureError
    from app.infrastructure.db.repositories.payment_repository import PaymentRepository
    from app.infrastructure.payments.resolver import PaymentGatewayResolver

    who, provider = await env.salon(), FakeProvider()
    pending = await env.buy(who, provider, pay=False)
    order = pending["checkout"]["order_ref"]
    pay = provider.pay(order)
    settings = Settings(
        _env_file=None, environment="test", payment_provider="cashfree", cashfree_client_id="cid",
        cashfree_client_secret="secret", cashfree_easy_split_enabled=True,
        payment_platform_fee_percent=D("0"), payment_commission_base="online_amount",
        subscription_provider="razorpay", subscription_razorpay_key_id="rzp_test_subkey",
        subscription_razorpay_key_secret="k", subscription_razorpay_webhook_secret="w" * 40,
        subscription_grace_days=GRACE)
    resolver = PaymentGatewayResolver(settings, subscription_provider_port=provider)
    body, headers = webhook("payment.captured", order=order, payment=pay, amount_paise=34900,
                            event_id="evt_forged")
    bad = {**headers, "x-razorpay-signature": "0" * 64}
    before = await env.scalar("select count(*) from payment_webhook_events")
    async with env.session() as s:
        with pytest.raises(InvalidWebhookSignatureError):
            await PaymentWebhookUseCases(PaymentRepository(s), resolver, settings).ingest(
                "razorpay", body, bad)
    assert await env.scalar("select count(*) from payment_webhook_events") == before
    assert await env.subscriptions(who["salon_id"]) == []

    async with env.session() as s:
        ack, row_id = await PaymentWebhookUseCases(PaymentRepository(s), resolver, settings).ingest(
            "razorpay", body, headers)
    assert ack == "accepted"

    async def subscription_side() -> str:
        async with env.session() as s:
            uc = PaymentWebhookUseCases(
                PaymentRepository(s), resolver, settings,
                SubscriptionWebhookHandler(SubscriptionBillingRepository(s),
                                           resolver_for(provider, settings), settings))
            return await uc.process(row_id)

    ledger = LedgerEnv(str(env.engine.url.render_as_string(hide_password=False)))
    try:
        booking = await ledger.booking("500.00")
        await ledger.intent(booking, "500.00", "o_sim_1")

        async def booking_side():
            return await ledger.capture("o_sim_1", "500.00")

        sub_result, booking_result = await asyncio.gather(subscription_side(), booking_side())
    finally:
        await ledger.engine.dispose()
    assert sub_result == "processed" and booking_result == "applied"
    assert (await env.subscriptions(who["salon_id"]))[0]["status"] == "active"
    assert await env.scalar("select count(*) from booking_payments where order_ref = 'o_sim_1' "
                            "and status = 'captured'") == 1


async def test_subscription_events_are_deduped_per_provider_in_the_domain_log(env):
    who, provider = await env.salon(), FakeProvider()
    result = await env.buy(who, provider)
    (sub,) = await env.subscriptions(who["salon_id"])
    async with env.session() as s:
        repo = SubscriptionBillingRepository(s)
        ok = await repo.log_event(subscription_id=str(sub["id"]), provider="razorpay",
                                  reference=f"applied:{result['checkout']['billing_id']}",
                                  event_type="subscription_started", payload={})
        await s.commit()
    assert ok is False  # already logged by the activation itself


# ============================================================ worker and closure
async def test_reconciler_settles_expires_and_sweeps_on_real_data(env):
    who, provider = await env.salon(), FakeProvider()
    pending = await env.buy(who, provider, pay=False)
    provider.pay(pending["checkout"]["order_ref"])
    await env.backdate(pending["checkout"]["billing_id"])
    async with env.session() as s:
        counts = await SubscriptionReconciler(
            SubscriptionBillingRepository(s), resolver_for(provider, env.settings), env.settings).run()
    assert counts["settled"] == 1 and counts["errors"] == 0
    assert (await env.subscriptions(who["salon_id"]))[0]["status"] == "active"
    # an unpaid order past its expiry is closed locally
    other = await env.salon()
    unpaid = await env.buy(other, provider, pay=False)
    await env.backdate(unpaid["checkout"]["billing_id"], expired=True)
    async with env.session() as s:
        counts = await SubscriptionReconciler(
            SubscriptionBillingRepository(s), resolver_for(provider, env.settings), env.settings).run()
    assert counts["expired"] == 1
    assert (await env.one("select status from subscription_billing_records where id = :i",
                          i=unpaid["checkout"]["billing_id"]))["status"] == "expired"


async def test_closure_winds_down_renewal_orders_and_flags_unused_paid_time(env):
    who, provider = await env.salon(), FakeProvider()
    paid = await env.buy(who, provider)
    open_order = await env.buy(who, provider, pay=False)
    async with env.session() as s:
        counts = await SubscriptionBillingRepository(s).wind_down_salons(who["owner_id"])
        await s.commit()
    assert counts == {"renewals_cancelled": 1, "orders_expired": 1, "unused_periods_flagged": 1}
    assert (await env.subscriptions(who["salon_id"]))[0]["status"] == "cancelled"
    assert (await env.one("select status from subscription_billing_records where id = :i",
                          i=open_order["checkout"]["billing_id"]))["status"] == "expired"
    anomaly = await env.one("select kind, amount from payment_anomalies where salon_id = :s "
                            "and kind = 'subscription_unused_period'", s=who["salon_id"])
    assert anomaly["amount"] == D("349.00") and paid
    async with env.session() as s:  # idempotent
        again = await SubscriptionBillingRepository(s).wind_down_salons(who["owner_id"])
        await s.commit()
    assert again == {"renewals_cancelled": 0, "orders_expired": 0, "unused_periods_flagged": 0}
    # the provider order of the expired local row can still be paid later: it is held, not applied
    provider.pay(open_order["checkout"]["order_ref"])
    await env.run("update salons set owner_id = null, is_active = false where id = :s", s=who["salon_id"])
    async with env.session() as s:
        repo = SubscriptionBillingRepository(s)
        record = await repo.get_billing(open_order["checkout"]["billing_id"])
        await repo.mark_paid(str(record["id"]), "pay_late_1")
        assert await repo.apply(str(record["id"]), GRACE) == "blocked_closed"
        await s.commit()


async def test_account_deletion_blocks_a_live_subscription_and_rechecks_at_confirm(env):
    # Unit-level guarantee: see tests/unit/test_account_deletion_use_cases.py; here we prove the SQL
    # blocker counts the statuses a purchase produces, so the confirm-time re-check has teeth.
    from app.infrastructure.db.repositories.account_deletion_repository import (
        SQLAccountDeletionRepository,
    )

    who, provider = await env.salon(), FakeProvider()
    await env.buy(who, provider)
    async with env.session() as s:
        blockers = await SQLAccountDeletionRepository(s).count_blockers(who["owner_id"], "owner")
    assert blockers["active_subscriptions"] == 1
    async with env.session() as s:
        await env.usecases(s, provider).cancel(owner(who["owner_id"]))
    async with env.session() as s:
        blockers = await SQLAccountDeletionRepository(s).count_blockers(who["owner_id"], "owner")
    assert blockers["active_subscriptions"] == 0  # cancelled: deletion may proceed, paid time flagged


# ===================================================================== downgrade
async def test_0030_downgrades_and_upgrades_again_on_a_scratch_database():
    database = "sub_billing_down_" + uuid4().hex
    await _build(database)
    url = make_url(TEST_DB).set(database=database, drivername="postgresql+asyncpg").render_as_string(
        hide_password=False)
    try:
        await asyncio.to_thread(_alembic, url, "downgrade", "0029_payment_monetary_policy")
        engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
        async with engine.connect() as conn:
            gone = await conn.scalar(text("select to_regclass('public.subscription_billing_records')"))
            assert gone is None
            fn = await conn.scalar(text("select to_regprocedure('public.apply_subscription_billing_record(uuid,integer)')"))
            assert fn is None
        await engine.dispose()
        await asyncio.to_thread(_alembic, url, "upgrade", _TEST_HEAD)
        await asyncio.to_thread(_alembic, url, "upgrade", _TEST_HEAD)  # no-op twice
        engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
        async with engine.connect() as conn:
            assert await conn.scalar(text("select count(*) from subscription_plans where code like 'premium\\_%'")) == 3
            assert await conn.scalar(text("select to_regclass('public.subscription_billing_records')")) is not None
        await engine.dispose()
    finally:
        await _drop(database)


def _unused() -> None:  # keeps imports honest for linters when optional paths are skipped
    _ = (datetime, UTC, subscription_event_to_json)
