"""Regression coverage for QR, provider uploads, avatars and reports."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.api.v1.routes import media, owner, reports
from app.application.use_cases.media import MAX_IMAGE_BYTES, UploadAvatar
from app.application.use_cases.reports import SubmitReport
from app.core.config import Settings
from app.core.exceptions import (
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
    register_exception_handlers,
)
from app.domain.entities.profile import Role
from app.infrastructure.imagekit.storage import ImageKitStorageGateway
from tests.conftest import make_owner, make_profile

PNG = b"\x89PNG\r\n\x1a\n" + b"sample"


def imagekit_settings():
    return Settings(_env_file=None, environment="test", storage_provider="imagekit",
                    imagekit_private_key="test-private-key", imagekit_url_endpoint="https://ik.example.test/app",
                    public_api_base_url="https://api.example.test")


def client_for(router, prefix="/v1"):
    app = FastAPI()
    app.include_router(router, prefix=prefix)
    register_exception_handlers(app)
    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_authenticated_session] = lambda: Mock()
    return TestClient(app)


async def test_imagekit_ticket_tampering_and_expiration(monkeypatch):
    gateway = ImageKitStorageGateway(imagekit_settings())
    monkeypatch.setattr("app.infrastructure.imagekit.storage.time.time", lambda: 1000)
    url = await gateway.get_upload_url("", "avatars/user/image.png", "image/png")
    ticket = url.rsplit("/", 1)[1]
    assert gateway.verify_ticket(ticket)["path"] == "avatars/user/image.png"
    with pytest.raises(UnauthorizedError):
        gateway.verify_ticket(ticket + "0")
    monkeypatch.setattr("app.infrastructure.imagekit.storage.time.time", lambda: 1301)
    with pytest.raises(UnauthorizedError):
        gateway.verify_ticket(ticket)


async def test_imagekit_upload_uses_server_credentials(monkeypatch):
    post = AsyncMock(return_value=httpx.Response(200, json={"url": "https://ik.example.test/app/a/x.png"},
                                                request=httpx.Request("POST", "https://upload.imagekit.io")))
    fake = AsyncMock()
    fake.__aenter__.return_value.post = post
    monkeypatch.setattr("app.infrastructure.imagekit.storage.httpx.AsyncClient", lambda **kw: fake)
    gateway = ImageKitStorageGateway(imagekit_settings())
    assert await gateway.upload_bytes("", "a/x.png", PNG) == "https://ik.example.test/app/a/x.png"
    assert post.call_args.kwargs["auth"] == ("test-private-key", "")
    assert post.call_args.kwargs["data"]["useUniqueFileName"] == "false"
    post.return_value = httpx.Response(401, text="provider secret detail",
                                     request=httpx.Request("POST", "https://upload.imagekit.io"))
    with pytest.raises(ValidationError, match="ImageKit upload failed") as error:
        await gateway.upload_bytes("", "a/x.png", PNG)
    assert "provider secret detail" not in str(error.value)


async def test_avatar_upload_persists_only_actor_profile():
    repo, storage = AsyncMock(), AsyncMock()
    storage.upload_bytes.return_value = "https://cdn.example.test/avatar.png"
    actor = make_profile()
    url = await UploadAvatar(repo, storage).execute(actor, PNG, "image/png", "images")
    repo.update_profile.assert_awaited_once_with(actor.id, {"avatar_url": url})
    assert storage.upload_bytes.call_args.args[1].startswith(f"avatars/{actor.id}/")


@pytest.mark.parametrize("data,mime", [
    (b"<script>", "image/png"),
    (PNG, "text/html"),
    (b"", "image/png"),
    pytest.param(b"x" * (MAX_IMAGE_BYTES + 1), "image/png", id="oversized-image/png"),
])
async def test_avatar_rejects_invalid_images_before_upload(data, mime):
    repo, storage = AsyncMock(), AsyncMock()
    with pytest.raises(ValidationError):
        await UploadAvatar(repo, storage).execute(make_profile(), data, mime, "images")
    storage.upload_bytes.assert_not_awaited()
    repo.update_profile.assert_not_awaited()


async def test_avatar_provider_failure_does_not_update_profile():
    repo, storage = AsyncMock(), AsyncMock()
    storage.upload_bytes.side_effect = ValidationError("Provider unavailable")
    with pytest.raises(ValidationError):
        await UploadAvatar(repo, storage).execute(make_profile(), PNG, "image/png", "images")
    repo.update_profile.assert_not_awaited()


def test_avatar_multipart_contract(monkeypatch):
    repo, storage = AsyncMock(), AsyncMock()
    storage.upload_bytes.return_value = "https://cdn.example.test/avatar.png"
    monkeypatch.setattr(media, "PlatformRepository", lambda session: repo)
    client = client_for(media.router)
    client.app.dependency_overrides[get_storage_gateway] = lambda: storage
    response = client.post("/v1/customer/profile/avatar", files={"image": ("a.png", PNG, "image/png")})
    assert response.status_code == 200
    assert response.json() == {"avatar_url": "https://cdn.example.test/avatar.png"}


async def test_imagekit_put_compatibility(monkeypatch):
    config = imagekit_settings()
    monkeypatch.setattr(media, "settings", config)
    gateway = ImageKitStorageGateway(config)
    ticket = (await gateway.get_upload_url("", "a/x.png", "image/png")).rsplit("/", 1)[1]
    upload = AsyncMock()
    monkeypatch.setattr(ImageKitStorageGateway, "upload_bytes", upload)
    client = client_for(media.router)
    assert client.put(f"/v1/media/uploads/{ticket}", content=PNG,
                      headers={"Content-Type": "image/png"}).status_code == 204
    upload.assert_awaited_once_with("", "a/x.png", PNG, "image/png")
    upload.reset_mock()
    assert client.put(f"/v1/media/uploads/{ticket}", content=PNG,
                      headers={"Content-Type": "image/jpeg"}).status_code == 422
    upload.assert_not_awaited()


@pytest.mark.parametrize("fmt", ["url", "png", "svg"])
def test_owner_qr_does_not_require_storage(monkeypatch, fmt):
    uc = AsyncMock()
    uc.get_my_salon.return_value = {"qr_token": "abc123", "id": "salon", "name": "தமிழ் Salon"}
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
