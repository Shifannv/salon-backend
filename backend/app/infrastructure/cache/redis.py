"""Optional Redis cache client.

Gracefully degrades to a no-op when ``REDIS_URL`` is not configured,
so the application starts without Redis in local/test environments.

Only used for:
  - Catalog reads (short TTL — catalog changes rarely)
  - Idempotency keys on booking creation
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_TTL_SECONDS = 300      # 5 minutes
_IDEMPOTENCY_TTL_SECONDS = 60   # 1 minute


class RedisCache:
    """Async Redis wrapper with graceful no-op fallback.

    Call ``await RedisCache.create(settings)`` to get an instance.
    All methods silently return ``None`` / do nothing when Redis is absent.
    """

    def __init__(self, client: Any | None) -> None:
        # client is a redis.asyncio.Redis instance or None
        self._client = client

    @classmethod
    async def create(cls, redis_url: str | None) -> RedisCache:
        """Attempt to connect to Redis; return a no-op instance on failure."""

        if not redis_url:
            logger.info("REDIS_URL not set — cache disabled")
            return cls(None)
        try:
            import redis.asyncio as aioredis  # type: ignore[import]

            client = aioredis.from_url(redis_url, decode_responses=True)
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

    async def set_idempotency(self, key: str, value: Any) -> None:
        """Store an idempotency response with the booking-creation TTL."""

        await self.set(key, value, ttl=_IDEMPOTENCY_TTL_SECONDS)

    async def get_idempotency(self, key: str) -> Any | None:
        """Return a cached idempotency response or None."""

        return await self.get(key)

    async def close(self) -> None:
        """Close the Redis connection gracefully."""

        if self._client is not None:
            await self._client.aclose()
