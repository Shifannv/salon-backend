"""Regression coverage for QR, provider uploads, avatars and reports."""

from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.api.v1.routes import media, owner, reports
from app.application.use_cases.media import MAX_IMAGE_BYTES, UploadAvatar
from app.application.use_cases.reports import SubmitReport
from app.core.exceptions import ForbiddenError, ValidationError, register_exception_handlers
from app.domain.entities.profile import Role
from app.infrastructure.media.pillow_processor import PillowImageProcessor
from tests.conftest import make_owner, make_profile

_png = BytesIO()
Image.new("RGB", (64, 64), "blue").save(_png, "PNG")
PNG = _png.getvalue()


def client_for(router, prefix="/v1"):
    app = FastAPI()
    app.include_router(router, prefix=prefix)
    register_exception_handlers(app)
    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_authenticated_session] = lambda: Mock()
    return TestClient(app)


async def test_avatar_upload_persists_only_actor_profile():
    repo, storage = AsyncMock(), AsyncMock()
    storage.upload_processed_family.return_value = {
        "public_url": "https://cdn.example.test/avatar.webp", "variants": {},
        "family_id": "test-family", "policy_version": "webp-v2",
    }
    actor = make_profile()
    url = await UploadAvatar(repo, storage, PillowImageProcessor()).execute(actor, PNG, "image/png", "images")
    repo.update_profile.assert_awaited_once_with(actor.id, {"avatar_url": url})
    assert storage.upload_processed_family.call_args.args[1] == f"avatars/{actor.id}/"
    assert storage.upload_processed_family.call_args.args[2].variants[0].mime == "image/webp"


@pytest.mark.parametrize(
    "data,mime",
    [
        pytest.param(b"<script>", "image/png", id="signature-mismatch"),
        pytest.param(PNG, "text/html", id="unsupported-content-type"),
        pytest.param(b"", "image/png", id="empty-file"),
        pytest.param(b"x" * (MAX_IMAGE_BYTES + 1), "image/png", id="too-large"),
    ],
)
async def test_avatar_rejects_invalid_images_before_upload(data, mime):
    repo, storage = AsyncMock(), AsyncMock()
    with pytest.raises(ValidationError):
        await UploadAvatar(repo, storage, PillowImageProcessor()).execute(make_profile(), data, mime, "images")
    storage.upload_processed_family.assert_not_awaited()
    repo.update_profile.assert_not_awaited()


async def test_avatar_provider_failure_does_not_update_profile():
    repo, storage = AsyncMock(), AsyncMock()
    storage.upload_processed_family.side_effect = ValidationError("Provider unavailable")
    with pytest.raises(ValidationError):
        await UploadAvatar(repo, storage, PillowImageProcessor()).execute(make_profile(), PNG, "image/png", "images")
    repo.update_profile.assert_not_awaited()


def test_avatar_multipart_contract(monkeypatch):
    repo, storage = AsyncMock(), AsyncMock()
    storage.upload_processed_family.return_value = {
        "public_url": "https://cdn.example.test/avatar.webp", "variants": {},
        "family_id": "test-family", "policy_version": "webp-v2",
    }
    monkeypatch.setattr(media, "PlatformRepository", lambda session: repo)
    client = client_for(media.router)
    client.app.dependency_overrides[get_storage_gateway] = lambda: storage
    response = client.post("/v1/customer/profile/avatar", files={"image": ("a.png", PNG, "image/png")})
    assert response.status_code == 200
    assert response.json() == {
        "avatar_url": "https://cdn.example.test/avatar.webp", "variants": {},
        "family_id": "test-family", "policy_version": "webp-v2",
    }


@pytest.mark.parametrize("fmt", ["url", "png", "svg"])
def test_owner_qr_does_not_require_storage(monkeypatch, fmt):
    uc = AsyncMock()
    uc.get_business_salon.return_value = {"qr_token": "abc123", "id": "salon", "name": "தமிழ் Salon"}
    monkeypatch.setattr(owner, "_use_cases", lambda session: uc)
    monkeypatch.setattr(owner.settings, "public_api_base_url", "https://api.example.test")
    client = client_for(owner.router, "/v1/salons")
    client.app.dependency_overrides[get_storage_gateway] = lambda: (_ for _ in ()).throw(AssertionError())
    response = client.get(f"/v1/salons/me/qr?format={fmt}")
    assert response.status_code == 200
    if fmt == "svg":
        assert "<svg" in response.text
    else:
        assert response.json()["url"] == "https://api.example.test/v1/walkin/abc123/qr?format=png&scale=12"


def test_owner_qr_repeated_clicks_keep_the_same_salon_identity(monkeypatch):
    """The endpoint reads the owner's stored token and never generates a replacement."""

    uc = AsyncMock()
    uc.get_business_salon.return_value = {
        "qr_token": "permanent-owner-salon-token",
        "id": "salon-001",
        "name": "Owner Salon",
    }
    monkeypatch.setattr(owner, "_use_cases", lambda session: uc)
    monkeypatch.setattr(owner.settings, "public_api_base_url", "https://api.example.test")
    client = client_for(owner.router, "/v1/salons")

    first = client.get("/v1/salons/me/qr")
    second = client.get("/v1/salons/me/qr")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert "permanent-owner-salon-token" in first.json()["url"]
    assert uc.get_business_salon.await_count == 2


async def test_report_authorization_and_actor_identity():
    repo = AsyncMock()
    actor = make_profile()
    await SubmitReport(repo).execute(actor, "salon", "reason", "details")
    repo.create_salon_report.assert_awaited_once_with(actor.id, "salon", "reason", "details")
    with pytest.raises(ForbiddenError):
        await SubmitReport(repo).execute(make_profile(role=Role.staff), "salon", "reason", "details")


def test_report_frontend_contract_ignores_client_identity_and_timestamp(monkeypatch):
    repo = AsyncMock()
    repo.create_salon_report.return_value = {"id": "11111111-1111-1111-1111-111111111111", "status": "received"}
    monkeypatch.setattr(reports, "PlatformRepository", lambda session: repo)
    client = client_for(reports.router)
    response = client.post("/v1/reports", json={
        "salon_id": "22222222-2222-2222-2222-222222222222", "salon_name": "Untrusted name",
        "reason": "Service issue", "details": "Details", "created_at": "2000-01-01T00:00:00Z",
        "reporter_id": "someone-else",
    })
    assert response.status_code == 201
    assert repo.create_salon_report.call_args.args == (
        "owner-001", "22222222-2222-2222-2222-222222222222", "Service issue", "Details",
    )
