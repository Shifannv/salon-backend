"""Feature access (0055) on disposable local PostgreSQL: seeds, constraints, cascade and the repository reads."""

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.infrastructure.db.repositories.feature_access_repository import FeatureAccessRepository
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SIDECAR = Path(__file__).parents[2] / "migrations/sql/0055_feature_access.sql"
PREMIUM_ONLY = {"split_bill", "rank_boost", "smart_slot_filler", "sms_alerts"}


@pytest.fixture(scope="module")
def access_db(changes_db):  # noqa: F811
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
async def env(access_db):
    environment = SafetyEnv(access_db)
    yield environment
    await environment.engine.dispose()


async def test_every_feature_is_seeded_for_all_three_audiences(env):
    async with env.session() as session:
        matrix = await FeatureAccessRepository(session).matrix()
    assert set(matrix) >= {"split_bill", "daily_ledger", "expenses", "finance_page", "reports", "staff_earnings", "wallet"}
    assert all(set(columns) == {"trial", "growth", "premium"} for columns in matrix.values())


async def test_seeded_defaults_open_everything_for_trial_and_premium_and_lock_the_premium_extras_for_growth(env):
    async with env.session() as session:
        matrix = await FeatureAccessRepository(session).matrix()
    for key, columns in matrix.items():
        assert columns["trial"] is True and columns["premium"] is True, key
        assert columns["growth"] is (key not in PREMIUM_ONLY), key


async def test_plan_copy_is_seeded_for_both_paid_tiers(env):
    async with env.session() as session:
        content = await FeatureAccessRepository(session).plan_content()
    assert set(content) == {"growth", "premium"}
    assert content["growth"]["bullets"] == []


async def test_an_unknown_audience_or_tier_is_refused(env):
    async with env.session() as session:
        with pytest.raises((DBAPIError, IntegrityError)):
            await session.execute(text(
                "insert into feature_plan_access(feature_key, audience, enabled) values ('wallet', 'gold', true)"
            ))
        await session.rollback()
        with pytest.raises((DBAPIError, IntegrityError)):
            await session.execute(text("insert into plan_tier_content(tier) values ('platinum')"))
        await session.rollback()


async def test_a_matrix_cell_for_an_unknown_feature_is_refused_by_the_repository(env):
    from app.core.exceptions import NotFoundError

    async with env.session() as session:
        with pytest.raises(NotFoundError):
            await FeatureAccessRepository(session).save_matrix(
                [{"feature_key": "nope", "audience": "growth", "enabled": True}], "00000000-0000-0000-0000-000000000000"
            )


async def test_saving_the_matrix_changes_one_cell_and_leaves_the_rest(env):
    async with env.session() as session:
        repo = FeatureAccessRepository(session)
        before = await repo.matrix()
        await repo.save_matrix([{"feature_key": "split_bill", "audience": "growth", "enabled": True}], None)
        after = await repo.matrix()
        # restore the seed so the other tests in this module still see the defaults
        await repo.save_matrix([{"feature_key": "split_bill", "audience": "growth", "enabled": False}], None)
    assert before["split_bill"]["growth"] is False and after["split_bill"]["growth"] is True
    assert {k: v for k, v in after["split_bill"].items() if k != "growth"} == {k: v for k, v in before["split_bill"].items() if k != "growth"}
    assert after["reports"] == before["reports"]
