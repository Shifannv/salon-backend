"""Cache gateway port."""

from abc import ABC, abstractmethod
from typing import Any


class CacheGateway(ABC):
    """Abstract interface for distributed caching, idempotency, and rate limiting."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """True when a live cache backend connection exists."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Return the decoded value or None on cache miss / unavailable cache."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Store a JSON-serialisable value with a TTL in seconds."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove a key from the cache."""

    @abstractmethod
    async def delete_prefix(self, prefix: str, *, strict: bool = False) -> None:
        """Remove all keys matching the prefix.

        Cache errors are swallowed by default (a cache miss is harmless). ``strict=True``
        re-raises them, for callers - like account erasure - that must know the data is gone.
        """

    @abstractmethod
    async def set_idempotency(self, key: str, value: Any) -> None:
        """Store an idempotency payload."""

    @abstractmethod
    async def get_idempotency(self, key: str) -> Any | None:
        """Retrieve a cached idempotency payload."""

    @abstractmethod
    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Check rate limit. Returns (allowed, remaining_quota)."""

    @abstractmethod
    async def ping(self) -> bool:
        """Return True if the cache backend is reachable."""

    @abstractmethod
    async def close(self) -> None:
        """Close connection cleanly."""
