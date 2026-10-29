"""Disposable PostgreSQL proof: approval grants, adjustments, isolation and locks."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from support_subscription import FakeProvider
from test_payment_ledger_sql import TEST_DB, _build, _drop
from test_subscription_billing_sql import Env, _apply_prepared

from app.core.exceptions import ConflictError
from app.domain.services.trial_limits import TrialLimits
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.repositories.trial_repository import SalonTrialRepository

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


@pytest.fixture(scope="module")
def db_url():
    database = "salon_trials_" + uuid4().hex
    asyncio.run(_build(database))
    url = make_url(TEST_DB).set(database=database, drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    asyncio.run(_apply_prepared(url, "0049_trial_salon_plan_prices.sql", "0050_plan_price_valid_until.sql"))
    yield url
    asyncio.run(_drop(database))


@pytest.fixture
def env(db_url):
    instance = Env(db_url)
    yield instance
    asyncio.run(instance.engine.dispose())


async def pending(env):
    who = await env.salon()
    # Fixture construction disabled triggers; create the ordinary pending access row.
    await env.run("update salons set approval_status='pending' where id=:s", s=who['salon_id'])
    return who


async def test_approval_grants_exact_limits_atomically_and_retry_preserves_usage(env):
    who = await pending(env)
    salon = who['salon_id']
    async with env.session() as session:
        await PlatformRepository(session).admin_set_salon_approval(
            salon, "approved", who['owner_id'], None, trial_limits=TrialLimits(14, 50)
        )
        trial = await SalonTrialRepository(session).get_trial(salon)
    assert trial['trial_days'] == 14 and trial['trial_booking_limit'] == 50
    started = trial['trial_started_at']
    await env.run("update salon_access set bookings_counted=7 where salon_id=:s", s=salon)
    async with env.session() as session:
        await PlatformRepository(session).admin_set_salon_approval(
            salon, "approved", who['owner_id'], None, trial_limits=TrialLimits(60, 500)
        )
        trial = await SalonTrialRepository(session).get_trial(salon)
    assert trial['trial_started_at'] == started
    assert trial['trial_days'] == 14 and trial['trial_booking_limit'] == 50
    assert trial['bookings_counted'] == 7


async def test_trial_adjustment_preserves_usage_and_changes_real_eligibility_only_for_target(env):
    who, other = await pending(env), await pending(env)
    salon = who['salon_id']
    await env.run("update salons set approval_status='approved' where id=:s", s=salon)
    before = await env.one("select * from salon_access where salon_id=:s", s=salon)
    await env.run("update salon_access set bookings_counted=12 where salon_id=:s", s=salon)
    async with env.session() as session:
        repo = SalonTrialRepository(session)
        lowered = await repo.update_trial(salon, TrialLimits(30, 10), who['owner_id'])
        untouched = await repo.get_trial(other['salon_id'])
    assert lowered['bookings_counted'] == 12 and lowered['state'] == 'quota_reached'
    assert not await env.scalar("select salon_booking_eligible(:s)", s=salon)
    assert untouched['state'] == 'not_started'
    async with env.session() as session:
        extended = await SalonTrialRepository(session).update_trial(salon, TrialLimits(45, 75), who['owner_id'])
    assert extended['trial_started_at'] == before['trial_started_at']
    assert extended['bookings_counted'] == 12 and extended['state'] == 'active'
    assert extended['trial_limit_reached_at'] is None
    assert await env.scalar("select salon_booking_eligible(:s)", s=salon)
    assert await env.scalar("select trial_ended_reason from salon_access where salon_id=:s", s=salon) is None


async def test_unstarted_trial_is_not_started_by_subscription_editor(env):
    who = await pending(env)
    async with env.session() as session:
        with pytest.raises(ConflictError):
            await SalonTrialRepository(session).update_trial(who['salon_id'], TrialLimits(14, 50), who['owner_id'])
        await session.rollback()
    assert await env.scalar("select trial_started_at from salon_access where salon_id=:s", s=who['salon_id']) is None


async def test_failed_initial_trial_update_rolls_back_the_approval(env, monkeypatch):
    who = await pending(env)

    async def fail(*args):
        raise ConflictError("Synthetic trial write failure")

    monkeypatch.setattr(SalonTrialRepository, 'apply_limits', fail)
    async with env.session() as session:
        with pytest.raises(ConflictError):
            await PlatformRepository(session).admin_set_salon_approval(
                who['salon_id'], 'approved', who['owner_id'], None, trial_limits=TrialLimits(14, 50)
            )
        await session.rollback()
    assert await env.scalar("select approval_status::text from salons where id=:s", s=who['salon_id']) == 'pending'
    assert await env.scalar("select trial_started_at from salon_access where salon_id=:s", s=who['salon_id']) is None


async def test_expiring_trial_does_not_change_paid_subscription_or_access(env):
    who = await pending(env)
    salon = who['salon_id']
    await env.run("update salons set approval_status='approved' where id=:s", s=salon)
    await env.buy(who, FakeProvider(env.settings))
    paid = await env.one("select * from salon_subscriptions where salon_id=:s", s=salon)
    await env.run("update salon_access set trial_started_at=now()-interval '5 days' where salon_id=:s", s=salon)
    async with env.session() as session:
        trial = await SalonTrialRepository(session).update_trial(salon, TrialLimits(1, 50), who['owner_id'])
    assert trial['state'] == 'expired'
    assert await env.scalar("select salon_booking_eligible(:s)", s=salon)
    assert await env.one("select * from salon_subscriptions where salon_id=:s", s=salon) == paid


async def test_update_and_booking_foreign_key_lock_do_not_deadlock(env):
    who = await pending(env)
    salon = who['salon_id']
    await env.run("update salons set approval_status='approved' where id=:s", s=salon)
    async with env.session() as booking, env.session() as admin:
        await booking.execute(text("select salon_id from salon_access where salon_id=:s for update"), {'s':salon})
        update = asyncio.create_task(SalonTrialRepository(admin).update_trial(salon, TrialLimits(14, 50), who['owner_id']))
        try:
            await asyncio.sleep(0.05)
            await asyncio.wait_for(booking.execute(text("select id from salons where id=:s for key share"), {'s':salon}), timeout=2)
            await booking.commit()
            await asyncio.wait_for(update, timeout=3)
        finally:
            if not update.done():
                update.cancel()
                await asyncio.gather(update, return_exceptions=True)
