"""Regression checks for admin review and isolated QR booking contexts."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_cache, get_current_actor, get_session
from app.api.v1.schemas.admin import AdminSalonResponse
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.main import app
from tests.conftest import make_booking, make_profile
from tests.unit.test_cache_integration import InMemoryCache


@pytest.mark.asyncio
async def test_admin_list_selects_required_review_and_owner_fields():
    """Exercise production SQL against a real SQLite table, not a repository mock."""
    from tests.unit.test_public_salon_visibility import SQLiteSession

    session = SQLiteSession()
    try:
        session.db.execute("delete from salons")
        for declaration in (
            "owner_id text", "approved_at text", "approved_by text", "rejection_reason text",
            "created_at text", "updated_at text", "updated_by text",
        ):
            session.db.execute(f"alter table salons add column {declaration}")
        session.db.execute("create table profiles (id text, email text, full_name text, phone text, "
                           "avatar_url text, phone_verified bool, is_active bool)")
        session.db.execute("insert into profiles values ('owner','owner@example.com','Owner','123',null,1,1)")
        session.db.execute("insert into salons (id,owner_id,name,timezone,approval_mode,approval_status,"
                           "profile_completed,is_active,working_hours,created_at,updated_at) "
                           "values ('salon','owner','Shop','UTC','auto','pending',1,1,'{}',"
                           "'2026-10-09T00:00:00Z','2026-10-09T00:00:00Z')")
        rows = await PlatformRepository(session).admin_list_salons(None, 20, 0)
        salon = AdminSalonResponse(**rows[0])
        assert salon.approval_status == "pending"
        assert salon.owner_phone == "123"
        assert salon.discovery_visibility == "listed"
    finally:
        session.db.close()


@pytest.fixture
def qr_client():
    overrides = app.dependency_overrides.copy()
    cache = InMemoryCache()
    actor = make_profile()
    uc = AsyncMock(unsafe=True)
    uc.assert_public_qr_token.side_effect = lambda token: {"qr-a": "salon-a", "qr-b": "salon-b"}[token]
    async def validate_context(actor, token, values):
        salon_id = await uc.assert_public_qr_token(token)
        if values["salon_id"] != salon_id:
            raise ValidationError("salon_id does not match the QR token")
        return salon_id
    uc.validate_booking_context.side_effect = validate_context
    uc.resolve_qr_token.side_effect = lambda token: {
        "id": {"qr-a": "salon-a", "qr-b": "salon-b"}[token],
        "name": token, "timezone": "UTC", "approval_mode": "auto",
    }
    app.dependency_overrides[get_current_actor] = lambda: actor
    app.dependency_overrides[get_session] = lambda: None
    app.dependency_overrides[get_authenticated_session] = lambda: None
    app.dependency_overrides[get_cache] = lambda: cache
    with patch("app.api.v1.routes.walkin._use_cases", return_value=uc):
        try:
            yield TestClient(app), cache, uc
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(overrides)


def test_qr_cache_cannot_return_other_salon_and_fresh_bypasses_cache(qr_client):
    client, cache, uc = qr_client
    cache._store["walkin:qr:qr-a"] = {
        "id": "salon-b", "name": "Wrong", "timezone": "UTC", "approval_mode": "auto",
    }
    assert client.get("/v1/walkin/qr-a").json()["id"] == "salon-a"
    assert client.get("/v1/walkin/qr-b").json()["id"] == "salon-b"
    client.get("/v1/walkin/qr-a?fresh=true")
    assert uc.resolve_qr_token.await_count == 3


def test_invalid_qr_cannot_send_otp(qr_client):
    client, _, uc = qr_client
    uc.assert_public_qr_token.side_effect = NotFoundError("Salon not found")
    gateway = AsyncMock()
    with patch("app.api.v1.routes.walkin.SupabaseAuthGateway", return_value=gateway):
        assert client.post("/v1/walkin/qr-a/verify-phone", json={"phone": "+919876543210"}).status_code == 404
    gateway.send_phone_otp.assert_not_awaited()


def test_qr_idempotency_is_token_scoped_and_payload_bound(qr_client):
    client, cache, _ = qr_client
    payload = {"salon_id": "salon-a", "staff_id": "staff-a", "service_ids": ["service-a"],
               "start_datetime": datetime.now(UTC).isoformat(), "customer_name": "Customer"}
    use_cases = AsyncMock()
    use_cases.create_walkin_booking.return_value = make_booking(salon_id="salon-a")
    headers = {"Idempotency-Key": "same-attempt"}
    with patch("app.api.v1.routes.walkin.WalkInUseCases", return_value=use_cases):
        assert client.post("/v1/walkin/qr-a/bookings", json=payload, headers=headers).status_code == 201
        assert client.post("/v1/walkin/qr-a/bookings", json=payload, headers=headers).status_code == 201
        assert use_cases.create_walkin_booking.await_count == 1
        changed = {**payload, "customer_name": "Changed"}
        assert client.post("/v1/walkin/qr-a/bookings", json=changed, headers=headers).status_code == 409
        assert client.post("/v1/walkin/qr-b/bookings", json=payload, headers=headers).status_code == 422
        use_cases.create_walkin_booking.return_value = make_booking(salon_id="salon-b")
        assert client.post("/v1/walkin/qr-b/bookings", json={**payload, "salon_id": "salon-b"},
                           headers=headers).status_code == 201
    assert len([key for key in cache._store if key.startswith("idempotency:")]) == 2


def test_qr_replay_revalidates_publication(qr_client):
    client, cache, uc = qr_client
    cache._store["idempotency:walkin:v2:user-001:qr-a:key"] = {}
    uc.assert_public_qr_token.side_effect = NotFoundError("Salon not found")
    payload = {"salon_id": "salon-a", "staff_id": "staff-a", "service_ids": ["service-a"],
               "start_datetime": datetime.now(UTC).isoformat(), "customer_name": "Customer"}
    assert client.post("/v1/walkin/qr-a/bookings", json=payload,
                       headers={"Idempotency-Key": "key"}).status_code == 404
