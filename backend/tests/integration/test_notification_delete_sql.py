"""Notification dismissal and retention (0066) on disposable local PostgreSQL."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.exceptions import NotFoundError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SIDECAR = Path(__file__).parents[2] / "migrations/sql/0066_notification_soft_delete.sql"


@pytest.fixture(scope="module")
def notifications_db(changes_db):  # noqa: F811
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
async def env(notifications_db):
    environment = SafetyEnv(notifications_db)
    yield environment
    await environment.engine.dispose()


async def notify(env, user, **overrides):
    raw = {"id": str(uuid4()), "user": user, "age": "0 days", "gone": None, **overrides}

    def _days(s: str) -> timedelta:
        return timedelta(days=int(s.split()[0]))

    now = datetime.now(tz=timezone.utc)
    await env.sql(
        """insert into notifications(id, user_id, title, created_at, deleted_at)
           values(:id, :user, 'Synthetic', :created_at, :deleted_at)""",
        id=raw["id"],
        user=raw["user"],
        created_at=now - _days(raw["age"]),
        deleted_at=now - _days(raw["gone"]) if raw["gone"] is not None else None,
    )
    return raw["id"]


async def repo_call(env, method, *args, **kwargs):
    async with env.session() as session:
        return await getattr(PlatformRepository(session), method)(*args, **kwargs)


async def deleted_at(env, notification):
    rows = await env.sql("select deleted_at from notifications where id = :id", id=notification)
    return rows[0]["deleted_at"]


async def test_dismissed_rows_leave_the_list_and_others_are_untouched(env):
    fixture = await env.seed()
    mine, mine_kept = await notify(env, fixture["owner"]), await notify(env, fixture["owner"])
    theirs = await notify(env, fixture["customer"])
    await repo_call(env, "delete_notifications", fixture["owner"], [mine, theirs, str(uuid4())])
    listed = await repo_call(env, "list_notifications", fixture["owner"])
    assert [row["id"] for row in listed] == [mine_kept]
    assert await deleted_at(env, mine) is not None
    assert await deleted_at(env, theirs) is None
    assert len(await repo_call(env, "list_notifications", fixture["customer"])) == 1


async def test_repeat_delete_keeps_the_first_timestamp(env):
    fixture = await env.seed()
    row = await notify(env, fixture["owner"])
    await repo_call(env, "delete_notifications", fixture["owner"], [row])
    first = await deleted_at(env, row)
    await repo_call(env, "delete_notifications", fixture["owner"], [row])
    assert await deleted_at(env, row) == first


async def test_a_dismissed_row_cannot_be_marked_read(env):
    fixture = await env.seed()
    row = await notify(env, fixture["owner"])
    await repo_call(env, "delete_notifications", fixture["owner"], [row])
    with pytest.raises(NotFoundError):
        await repo_call(env, "mark_notification_read", fixture["owner"], row)
    rows = await env.sql("select read from notifications where id = :id", id=row)
    assert rows[0]["read"] is False


async def test_read_all_ignores_dismissed_rows(env):
    fixture = await env.seed()
    live, gone = await notify(env, fixture["owner"]), await notify(env, fixture["owner"])
    await repo_call(env, "delete_notifications", fixture["owner"], [gone])
    assert await repo_call(env, "mark_all_notifications_read", fixture["owner"]) == 1
    rows = await env.sql("select id, read from notifications where id in (:a, :b)", a=live, b=gone)
    assert {str(row["id"]): row["read"] for row in rows} == {live: True, gone: False}


async def test_retention_purges_old_dismissed_and_expired_rows_in_bounded_batches(env):
    fixture = await env.seed()
    user = fixture["owner"]
    fresh = await notify(env, user)
    dismissed_recently = await notify(env, user, gone="29 days")
    dismissed_long_ago = [await notify(env, user, gone="31 days") for _ in range(3)]
    expired = await notify(env, user, age="61 days")
    kept_old = await notify(env, user, age="59 days")
    args = {"dismissed_days": 30, "max_age_days": 60}
    assert await repo_call(env, "purge_notifications", limit=2, **args) == 2
    assert await repo_call(env, "purge_notifications", limit=10, **args) == 2
    assert await repo_call(env, "purge_notifications", limit=10, **args) == 0
    survivors = {str(row["id"]) for row in await env.sql(
        "select id from notifications where user_id = :user", user=user)}
    assert survivors == {fresh, dismissed_recently, kept_old}
    assert not survivors & {expired, *dismissed_long_ago}


async def test_account_erasure_delete_also_removes_dismissed_rows(env):
    fixture = await env.seed()
    row = await notify(env, fixture["customer"], gone="1 days")
    await env.sql("delete from notifications where user_id = :user", user=fixture["customer"])
    assert await env.sql("select 1 from notifications where id = :id", id=row) == []
