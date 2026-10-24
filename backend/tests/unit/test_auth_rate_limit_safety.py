from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ServiceUnavailableError
from app.infrastructure.cache.redis import RedisCache


async def test_auth_limit_fails_closed_without_redis_but_booking_fallback_stays_available():
    cache = RedisCache(None)
    with pytest.raises(ServiceUnavailableError):
        await cache.check_rate_limit('auth:test', 5, 60, strict=True)
    assert await cache.check_rate_limit('booking:test', 5, 60) == (True, 5)


async def test_auth_limit_fails_closed_on_backend_error():
    cache = RedisCache(AsyncMock())
    cache._client.eval.side_effect = OSError('synthetic outage')
    with pytest.raises(ServiceUnavailableError):
        await cache.check_rate_limit('auth:test', 5, 60, strict=True)
