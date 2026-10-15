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
import time
from contextvars import ContextVar
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from app.application.ports.cache_gateway import CacheGateway
from app.core.telemetry import metrics

logger = logging.getLogger(__name__)

_CATALOG_TTL_SECONDS = 300      # 5 minutes
_IDEMPOTENCY_TTL_SECONDS = 60   # 1 minute
_READ_EPOCH = "read-model:epoch:v1"
_READ_PREFIXES = ("salon:", "catalog:", "walkin:qr:")
_LIVE_PREFIXES = ("availability:", "slot:", "slots:", "booking:", "bookings:")
_read_versions: ContextVar[dict[str, str] | None] = ContextVar("cache_read_versions", default=None)


def _redacted_target(redis_url: str) -> str:
    """Host and port only: the URL carries the Redis password."""
    parsed = urlsplit(redis_url)
    if not parsed.hostname:
        return "<redis>"
    return f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname


class RedisCache(CacheGateway):
    """Async Redis wrapper with graceful no-op fallback."""

    def __init__(self, client: Any | None) -> None:
        self._client = client
        self._read_cache_safe = True

    async def invalidate_read_models(self) -> None:
        """After DB commit, retire every public read snapshot without deleting replay keys.

        Broad invalidation also covers worker/admin/closure mutations. Versioned
        keys ensure a slow pre-commit reader cannot repopulate the current epoch.
        Old generations expire with their existing bounded TTL.
        """
        if self._client is None:
            return
        try:
            await self._client.set(_READ_EPOCH, uuid4().hex)
            self._read_cache_safe = True
            # One atomic namespace change invalidates logical read keys. Do not
            # SCAN the keyspace on every commit. Explicit erasure delete_prefix
            # still removes payloads from every generation, not just the pointer.
        except Exception:
            self._read_cache_safe = False
            logger.warning("Read cache invalidation failed; this process will bypass payload caching")

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
            logger.info("Redis cache connected at %s", _redacted_target(redis_url))
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
        if key.startswith(_LIVE_PREFIXES):
            return None
        started = time.perf_counter()
        current = metrics.get()
        if current is not None:
            current.cache_reads += 1
        try:
            if key.startswith(_READ_PREFIXES):
                if not self._read_cache_safe:
                    return None
                version = await self._client.get(_READ_EPOCH) or "initial"
                versions = dict(_read_versions.get() or {})
                versions[key] = version
                _read_versions.set(versions)
                key = f"read-model:v1:{version}:{key}"
            raw = await self._client.get(key)
            if raw and current is not None:
                current.cache_hits += 1
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.debug("Redis GET error for key %s: %s", key, exc)
            return None
        finally:
            if current is not None:
                current.redis_duration_ms += (time.perf_counter() - started) * 1000

    async def set(self, key: str, value: Any, ttl: int = _CATALOG_TTL_SECONDS) -> None:
        """Store a JSON-serialisable value with a TTL."""
        if self._client is None:
            return
        if key.startswith(_LIVE_PREFIXES):
            return
        try:
            if key.startswith(_READ_PREFIXES):
                version = (_read_versions.get() or {}).get(key)
                if not self._read_cache_safe or version is None:
                    return
                key = f"read-model:v1:{version}:{key}"
                await self._client.eval(
                    "if (redis.call('GET', KEYS[1]) or 'initial') == ARGV[1] then "
                    "return redis.call('SETEX', KEYS[2], ARGV[2], ARGV[3]) end return nil",
                    2, _READ_EPOCH, key, version, ttl, json.dumps(value, default=str),
                )
                return
            await self._client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.debug("Redis SET error for key %s: %s", key, exc)

    async def delete(self, key: str) -> None:
        """Remove a key (e.g. after a catalog write invalidates the cache)."""
        if self._client is None:
            return
        try:
            await self._client.delete(key)
            if key.startswith(_READ_PREFIXES):
                # Existing explicit invalidations remain useful during a rolling upgrade.
                await self._client.set(_READ_EPOCH, uuid4().hex)
        except Exception as exc:
            logger.debug("Redis DEL error for key %s: %s", key, exc)

    async def delete_prefix(self, prefix: str, *, strict: bool = False) -> None:
        """Remove all keys matching a prefix (e.g. invalidating a catalog subset).

        ``strict`` re-raises Redis errors instead of logging them at debug level.
        """
        if self._client is None:
            return
        try:
            if any(prefix.startswith(root) or root.startswith(prefix) for root in _READ_PREFIXES):
                await self._client.set(_READ_EPOCH, uuid4().hex)
            keys: list[str] = []
            async for matched_key in self._client.scan_iter(match=f"{prefix}*"):
                keys.append(matched_key)
            if any(prefix.startswith(root) or root.startswith(prefix) for root in _READ_PREFIXES):
                async for matched_key in self._client.scan_iter(match=f"read-model:v1:*:{prefix}*"):
                    keys.append(matched_key)
            if keys:
                await self._client.delete(*keys)
        except Exception as exc:
            if strict:
                raise
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
