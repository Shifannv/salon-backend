"""Redis cache client implementing CacheGateway.

Gracefully degrades to a no-op when ``REDIS_URL`` is not configured or
unreachable, so the application functions without Redis in local/test environments.

Used for:
  - Service catalog & public salon data caching
  - Idempotency keys on booking creation
  - Rate limiting on sensitive public endpoints (OTP requests)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.application.ports.cache_gateway import CacheGateway

logger = logging.getLogger(__name__)

_CATALOG_TTL_SECONDS = 300      # 5 minutes
_IDEMPOTENCY_TTL_SECONDS = 60   # 1 minute


class RedisCache(CacheGateway):
    """Async Redis wrapper with graceful no-op fallback."""

    def __init__(self, client: Any | None) -> None:
        self._client = client

    @classmethod
    async def create(cls, redis_url: str | None) -> RedisCache:
        """Attempt to connect to Redis; return a no-op instance on failure."""
        if not redis_url:
            logger.info("REDIS_URL not set — cache disabled")
            return cls(None)
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
            )
            await client.ping()
            logger.info("Redis cache connected at %s", redis_url)
            return cls(client)
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — cache disabled", exc)
            return cls(None)

    @property
    def available(self) -> bool:
        """True when a live Redis connection exists."""
        return self._client is not None

    async def ping(self) -> bool:
        """Return True if Redis is reachable, False otherwise."""
        if self._client is None:
            return False
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def get(self, key: str) -> Any | None:
        """Return the decoded value or None on cache miss / no Redis."""
        if self._client is None:
            return None
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.debug("Redis GET error for key %s: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl: int = _CATALOG_TTL_SECONDS) -> None:
        """Store a JSON-serialisable value with a TTL."""
        if self._client is None:
            return
        try:
            await self._client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.debug("Redis SET error for key %s: %s", key, exc)

    async def delete(self, key: str) -> None:
        """Remove a key (e.g. after a catalog write invalidates the cache)."""
        if self._client is None:
            return
        try:
            await self._client.delete(key)
        except Exception as exc:
            logger.debug("Redis DEL error for key %s: %s", key, exc)

    async def delete_prefix(self, prefix: str) -> None:
        """Remove all keys matching a prefix (e.g. invalidating a catalog subset)."""
        if self._client is None:
            return
        try:
            keys: list[str] = []
            async for matched_key in self._client.scan_iter(match=f"{prefix}*"):
                keys.append(matched_key)
            if keys:
                await self._client.delete(*keys)
        except Exception as exc:
            logger.debug("Redis DEL prefix error for %s: %s", prefix, exc)

    async def set_idempotency(self, key: str, value: Any) -> None:
        """Store an idempotency response with the booking-creation TTL."""
        await self.set(key, value, ttl=_IDEMPOTENCY_TTL_SECONDS)

    async def get_idempotency(self, key: str) -> Any | None:
        """Return a cached idempotency response or None."""
        return await self.get(key)

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Check rate limit using a fixed-window atomic counter.

        Returns (allowed, remaining).
        Gracefully returns (True, limit) when Redis is disabled or fails.
        """
        if self._client is None:
            return True, limit
        try:
            current = await self._client.incr(key)
            if current == 1:
                await self._client.expire(key, window_seconds)
            if current > limit:
                return False, 0
            return True, max(0, limit - current)
        except Exception as exc:
            logger.debug("Redis rate limit error for %s: %s", key, exc)
            return True, limit

    async def close(self) -> None:
        """Close the Redis connection gracefully."""
        if self._client is not None:
            await self._client.aclose()


_cache_instance: RedisCache | None = None


async def init_redis_cache(redis_url: str | None) -> RedisCache:
    """Initialize the process-wide Redis cache client."""
    global _cache_instance
    _cache_instance = await RedisCache.create(redis_url)
    return _cache_instance


async def close_redis_cache() -> None:
    """Close the process-wide Redis cache client."""
    global _cache_instance
    if _cache_instance is not None:
        await _cache_instance.close()
        _cache_instance = None


def get_redis_cache() -> RedisCache:
    """Return the initialized Redis cache, or an unconfigured no-op cache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache(None)
    return _cache_instance
