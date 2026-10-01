"""Unit tests for RedisCache infrastructure adapter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.cache.redis import (
    RedisCache,
    close_redis_cache,
    get_redis_cache,
    init_redis_cache,
)


@pytest.mark.asyncio
async def test_redis_cache_noop_when_client_is_none() -> None:
    cache = RedisCache(None)

    assert cache.available is False
    assert await cache.ping() is False
    assert await cache.get("any_key") is None
    await cache.set("any_key", {"foo": "bar"}, ttl=60)
    await cache.delete("any_key")
    await cache.delete_prefix("any_prefix:")
    await cache.set_idempotency("idem_key", {"status": "ok"})
    assert await cache.get_idempotency("idem_key") is None

    allowed, remaining = await cache.check_rate_limit("rate_key", limit=10, window_seconds=60)
    assert allowed is True
    assert remaining == 10

    await cache.close()


@pytest.mark.asyncio
async def test_redis_cache_create_returns_noop_on_none_or_empty_url() -> None:
    cache = await RedisCache.create(None)
    assert cache.available is False

    cache_empty = await RedisCache.create("")
    assert cache_empty.available is False


@pytest.mark.asyncio
async def test_redis_cache_create_handles_connection_failure() -> None:
    # Pointing to an invalid unreachable port
    cache = await RedisCache.create("redis://127.0.0.1:1/0")
    assert cache.available is False
    assert await cache.ping() is False


@pytest.mark.asyncio
async def test_redis_cache_operations_with_mock_client() -> None:
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = '{"hello": "world"}'
    mock_client.incr.return_value = 2

    cache = RedisCache(mock_client)
    assert cache.available is True
    assert await cache.ping() is True

    # Test GET
    result = await cache.get("test_key")
    assert result == {"hello": "world"}
    mock_client.get.assert_awaited_once_with("test_key")

    # Test SET
    await cache.set("test_key", {"a": 1}, ttl=120)
    mock_client.setex.assert_awaited_once_with("test_key", 120, '{"a": 1}')

    # Test DELETE
    await cache.delete("test_key")
    mock_client.delete.assert_awaited_once_with("test_key")

    # Test Rate limit: 2nd hit of 5
    allowed, remaining = await cache.check_rate_limit("rate:user1", limit=5, window_seconds=60)
    assert allowed is True
    assert remaining == 3

    # Test Rate limit exceeded
    mock_client.incr.return_value = 6
    allowed, remaining = await cache.check_rate_limit("rate:user1", limit=5, window_seconds=60)
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_redis_cache_delete_prefix_with_mock_client() -> None:
    mock_client = MagicMock()
    mock_client.delete = AsyncMock()

    async def async_scan_iter(match: str):
        yield "prefix:key1"
        yield "prefix:key2"

    mock_client.scan_iter = async_scan_iter

    cache = RedisCache(mock_client)
    await cache.delete_prefix("prefix:")

    mock_client.delete.assert_awaited_once_with("prefix:key1", "prefix:key2")


@pytest.mark.asyncio
async def test_redis_cache_global_lifecycle() -> None:
    cache = await init_redis_cache(None)
    assert cache.available is False
    assert get_redis_cache() is cache

    await close_redis_cache()
    # After close, get_redis_cache returns a fresh fallback noop
    new_cache = get_redis_cache()
    assert new_cache.available is False
