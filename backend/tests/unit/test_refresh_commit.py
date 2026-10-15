"""Read cache invalidation belongs after durable DB commit, never before it."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import MeasuredAsyncSession


@pytest.mark.asyncio
async def test_successful_commit_invalidates_after_database_commit():
    order = []

    async def commit():
        order.append("committed")

    cache = AsyncMock()
    cache.invalidate_read_models.side_effect = lambda: order.append("invalidated")
    with patch.object(AsyncSession, "commit", side_effect=commit), patch(
        "app.infrastructure.cache.redis.get_redis_cache", return_value=cache
    ):
        async with MeasuredAsyncSession() as session:
            await session.commit()
    assert order == ["committed", "invalidated"]


@pytest.mark.asyncio
async def test_failed_commit_does_not_invalidate_read_models():
    cache = AsyncMock()
    with patch.object(AsyncSession, "commit", side_effect=RuntimeError("commit failed")), patch(
        "app.infrastructure.cache.redis.get_redis_cache", return_value=cache
    ):
        async with MeasuredAsyncSession() as session:
            with pytest.raises(RuntimeError, match="commit failed"):
                await session.commit()
    cache.invalidate_read_models.assert_not_awaited()
