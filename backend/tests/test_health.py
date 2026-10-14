from fastapi.testclient import TestClient

from app.infrastructure.db.session import get_probe_session
from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_returns_safe_503_when_database_is_unavailable() -> None:
    class UnavailableSession:
        async def execute(self, _query):
            raise ConnectionError("secret connection detail")

    async def unavailable_session():
        yield UnavailableSession()

    app.dependency_overrides[get_probe_session] = unavailable_session
    try:
        response = TestClient(app).get("/health/db")
    finally:
        app.dependency_overrides.pop(get_probe_session, None)

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "service_unavailable", "message": "Database is unavailable"}
    }
    assert "secret connection detail" not in response.text


def test_redis_health_disabled_when_not_configured() -> None:
    from app.api.deps import get_cache
    from app.infrastructure.cache.redis import RedisCache

    app.dependency_overrides[get_cache] = lambda: RedisCache(None)
    try:
        response = TestClient(app).get("/health/redis")
    finally:
        app.dependency_overrides.pop(get_cache, None)

    assert response.status_code == 200
    assert response.json() == {"status": "disabled", "redis": "not configured"}


def test_redis_health_ok_when_reachable() -> None:
    from unittest.mock import AsyncMock

    from app.api.deps import get_cache
    from app.infrastructure.cache.redis import RedisCache

    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    cache = RedisCache(mock_client)

    app.dependency_overrides[get_cache] = lambda: cache
    try:
        response = TestClient(app).get("/health/redis")
    finally:
        app.dependency_overrides.pop(get_cache, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "reachable"}


def test_redis_health_returns_503_when_ping_fails() -> None:
    from unittest.mock import AsyncMock

    from app.api.deps import get_cache
    from app.infrastructure.cache.redis import RedisCache

    mock_client = AsyncMock()
    mock_client.ping.side_effect = ConnectionError("Connection refused")
    cache = RedisCache(mock_client)

    app.dependency_overrides[get_cache] = lambda: cache
    try:
        response = TestClient(app).get("/health/redis")
    finally:
        app.dependency_overrides.pop(get_cache, None)

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "service_unavailable", "message": "Redis is unavailable"}
    }
