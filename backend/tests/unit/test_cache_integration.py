"""Integration tests for Redis cache, idempotency, and rate limiting."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_cache, get_current_actor, get_session
from app.application.ports.cache_gateway import CacheGateway
from app.domain.entities.profile import Role
from app.main import app
from tests.conftest import make_booking, make_profile, make_super_admin


class InMemoryCache(CacheGateway):
    """In-memory CacheGateway test double."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._hits = 0
        self._misses = 0
        self._counter: dict[str, int] = {}

    @property
    def available(self) -> bool:
        return True

    async def get(self, key: str):
        if key in self._store:
            self._hits += 1
            return self._store[key]
        self._misses += 1
        return None

    async def set(self, key: str, value, ttl: int = 300):
        self._store[key] = value

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def delete_prefix(self, prefix: str):
        to_del = [k for k in self._store if k.startswith(prefix)]
        for k in to_del:
            del self._store[k]

    async def set_idempotency(self, key: str, value):
        await self.set(key, value, ttl=60)

    async def get_idempotency(self, key: str):
        return await self.get(key)

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int):
        val = self._counter.get(key, 0) + 1
        self._counter[key] = val
        if val > limit:
            return False, 0
        return True, limit - val

    async def ping(self):
        return True

    async def close(self):
        pass


def test_booking_creation_idempotency() -> None:
    client = TestClient(app)
    cache = InMemoryCache()
    actor = make_profile(id="user-123", role=Role.customer)

    now = datetime.now(UTC)
    start = now + timedelta(days=1)
    end = start + timedelta(minutes=30)
    fake_booking = make_booking(
        booking_id="booking-abc",
        customer_id=actor.id,
    )
    fake_booking["customer_name"] = "Alice Smith"
    fake_booking["start_datetime"] = start.isoformat()
    fake_booking["end_datetime"] = end.isoformat()

    mock_uc = AsyncMock()
    mock_uc.create_booking.return_value = fake_booking

    async def override_session():
        yield AsyncMock()

    app.dependency_overrides[get_current_actor] = lambda: actor
    app.dependency_overrides[get_authenticated_session] = override_session
    app.dependency_overrides[get_cache] = lambda: cache

    payload = {
        "salon_id": "00000000-0000-0000-0000-000000000001",
        "staff_id": "00000000-0000-0000-0000-000000000002",
        "service_ids": ["00000000-0000-0000-0000-000000000003"],
        "start_datetime": start.isoformat(),
        "customer_name": "Alice Smith",
        "notes": "First attempt",
    }

    try:
        with patch("app.api.v1.routes.bookings._use_cases", return_value=mock_uc):
            # First request with Idempotency-Key
            resp1 = client.post(
                "/v1/bookings",
                json=payload,
                headers={"Idempotency-Key": "key-xyz-123"},
            )
            assert resp1.status_code == 201
            assert resp1.json()["id"] == "booking-abc"
            assert mock_uc.create_booking.await_count == 1

            # Second request with identical Idempotency-Key
            resp2 = client.post(
                "/v1/bookings",
                json=payload,
                headers={"Idempotency-Key": "key-xyz-123"},
            )
            assert resp2.status_code == 201
            assert resp2.json()["id"] == "booking-abc"
            # Ensure the use case was NOT called again!
            assert mock_uc.create_booking.await_count == 1
    finally:
        app.dependency_overrides.pop(get_current_actor, None)
        app.dependency_overrides.pop(get_authenticated_session, None)
        app.dependency_overrides.pop(get_cache, None)


def test_public_categories_caching_and_invalidation() -> None:
    client = TestClient(app)
    cache = InMemoryCache()
    now_str = datetime.now(UTC).isoformat()

    mock_repo = AsyncMock()
    mock_repo.list_categories.return_value = [
        {
            "id": "cat-1",
            "name": "Haircuts",
            "slug": "haircuts",
            "icon_name": None,
            "sort_order": 1,
            "is_active": True,
            "created_at": now_str,
            "updated_at": now_str,
        }
    ]

    async def override_session():
        yield AsyncMock()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_cache] = lambda: cache

    try:
        with patch("app.api.v1.routes.customer.PlatformRepository", return_value=mock_repo):
            # First call: cache miss, calls repository
            resp1 = client.get("/v1/catalog/categories")
            assert resp1.status_code == 200
            assert len(resp1.json()) == 1
            assert mock_repo.list_categories.await_count == 1

            # Second call: cache hit, repository is not called again
            resp2 = client.get("/v1/catalog/categories")
            assert resp2.status_code == 200
            assert mock_repo.list_categories.await_count == 1
            assert cache._hits == 1

        # Now test cache invalidation on admin category creation
        admin_actor = make_super_admin()
        mock_admin_uc = AsyncMock()
        mock_admin_uc.create_category.return_value = {
            "id": "cat-2",
            "name": "Beards",
            "slug": "beards",
            "icon_name": None,
            "sort_order": 2,
            "is_active": True,
            "created_at": now_str,
            "updated_at": now_str,
        }

        app.dependency_overrides[get_current_actor] = lambda: admin_actor
        app.dependency_overrides[get_authenticated_session] = override_session

        with patch("app.api.v1.routes.admin._catalog_use_cases", return_value=mock_admin_uc):
            admin_resp = client.post(
                "/v1/admin/catalog/categories",
                json={"name": "Beards", "slug": "beards", "sort_order": 2},
            )
            assert admin_resp.status_code == 201
            # Cache key should now be removed
            assert "catalog:categories:active" not in cache._store
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_actor, None)
        app.dependency_overrides.pop(get_authenticated_session, None)
        app.dependency_overrides.pop(get_cache, None)


def test_walkin_verify_phone_rate_limiting() -> None:
    client = TestClient(app)
    cache = InMemoryCache()

    mock_gateway = AsyncMock()
    mock_gateway.send_phone_otp.return_value = None

    app.dependency_overrides[get_cache] = lambda: cache
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    try:
        with (
            patch("app.api.v1.routes.walkin.SupabaseAuthGateway", return_value=mock_gateway),
            patch("app.api.v1.routes.walkin._use_cases", return_value=AsyncMock(unsafe=True)),
        ):
            # Limit is 5 OTP requests per minute
            for _ in range(5):
                resp = client.post(
                    "/v1/walkin/token123/verify-phone",
                    json={"phone": "+919876543210"},
                )
                assert resp.status_code == 200

            # 6th request must fail with 429 Too Many Requests
            resp_exceeded = client.post(
                "/v1/walkin/token123/verify-phone",
                json={"phone": "+919876543210"},
            )
            assert resp_exceeded.status_code == 429
            data = resp_exceeded.json()
            assert data["error"]["code"] == "too_many_requests"
            assert "Too many OTP requests" in data["error"]["message"]
    finally:
        app.dependency_overrides.pop(get_cache, None)
        app.dependency_overrides.pop(get_session, None)
