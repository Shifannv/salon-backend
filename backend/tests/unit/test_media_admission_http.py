"""Admission errors follow the application's CORS, timing and error contract."""

import asyncio
from functools import partial
from unittest.mock import Mock
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.core import telemetry
from app.core.config import settings
from app.core.exceptions import TooManyRequestsError
from app.infrastructure.media.admission import UploadAdmissionMiddleware
from tests.conftest import make_profile
from tests.unit.media_r2_fake import FakeR2Client
from tests.unit.test_image_processing import gateway, photo_data

ORIGIN = "https://image-review.example"
REQUEST_ID = "admission-regression-123"


@pytest.fixture
def app_factory(monkeypatch):
    monkeypatch.setattr(settings, "backend_cors_origins", [ORIGIN])
    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(main, "init_sentry", lambda settings: False)

    def forbidden_dependency():
        raise AssertionError("Rejected admission must not reach authentication or database work")

    def build(*, environment="staging", **limits):
        monkeypatch.setattr(settings, "environment", environment)
        monkeypatch.setattr(main, "UploadAdmissionMiddleware", partial(UploadAdmissionMiddleware, **limits))
        app = main.create_app()
        app.dependency_overrides[get_current_actor] = forbidden_dependency
        app.dependency_overrides[get_authenticated_session] = forbidden_dependency
        app.dependency_overrides[get_storage_gateway] = forbidden_dependency
        return app

    return build


def oversized(client, origin=ORIGIN):
    return client.post("/v1/customer/profile/avatar", headers={
        "Origin": origin, "X-Request-ID": REQUEST_ID,
        "Content-Type": "multipart/form-data; boundary=synthetic",
        "Content-Length": str(5_242_880 + 65_536 + 1),
    })


def assert_error(response, status, code, message):
    assert response.status_code == status
    assert response.json() == {"error": {"code": code, "message": message}}
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["x-request-id"] == REQUEST_ID
    assert "app;dur=" in response.headers["server-timing"]


def test_allowed_origin_oversized_upload_has_shared_error_cors_and_timing(app_factory, monkeypatch):
    app = app_factory()
    parser = Mock(side_effect=AssertionError("Oversized body must not be parsed"))
    monkeypatch.setattr("starlette.requests.Request.form", parser)
    log = Mock()
    monkeypatch.setattr(telemetry, "_log", log)
    # No context manager: lifespan must not open DB/Redis connections.
    client = TestClient(app)
    try:
        response = oversized(client)
        assert_error(response, 413, "payload_too_large", "Image request is too large")
        assert "access-control-allow-credentials" not in response.headers
        assert "origin" in response.headers["vary"].lower()
        parser.assert_not_called()
        assert log.info.call_args.kwargs["status_code"] == 413
        assert log.info.call_args.kwargs["request_id"] == REQUEST_ID
        assert log.info.call_args.kwargs["error_code"] == "payload_too_large"
    finally:
        client.close()


def test_disallowed_origin_does_not_receive_allow_origin(app_factory):
    client = TestClient(app_factory())
    try:
        response = oversized(client, "https://untrusted.example")
        assert response.status_code == 413
        assert "access-control-allow-origin" not in response.headers
        assert response.headers["x-request-id"] == REQUEST_ID
        assert "server-timing" in response.headers
        assert response.json() == {"error": {
            "code": "payload_too_large", "message": "Image request is too large",
        }}
    finally:
        client.close()


def test_unsupported_type_and_rate_limit_keep_shared_handling_and_retry_after(app_factory):
    app = app_factory(rate_limit=1)

    @app.get("/admission-error-control", response_model=None, status_code=200)
    async def error_control():
        raise TooManyRequestsError("Too many image upload requests")

    client = TestClient(app)
    headers = {"Origin": ORIGIN, "X-Request-ID": REQUEST_ID, "Content-Type": "text/html"}
    try:
        first = client.put("/v1/media/uploads/synthetic", content=b"invalid", headers=headers)
        assert_error(first, 415, "unsupported_media_type", "Upload a JPEG, PNG or WebP image")
        second = client.put("/v1/media/uploads/synthetic", content=b"invalid", headers=headers)
        assert_error(second, 429, "too_many_requests", "Too many image upload requests")
        assert 1 <= int(second.headers["retry-after"]) <= 60
        control = client.get("/admission-error-control")
        assert second.json() == control.json()
    finally:
        client.close()


async def request_asgi(app, receive):
    sent = []

    async def send(message):
        sent.append(message)

    await app({
        "type": "http", "http_version": "1.1", "method": "PUT", "scheme": "https",
        "path": "/v1/media/uploads/synthetic", "root_path": "", "query_string": b"",
        "server": ("testserver", 443), "client": ("127.0.0.1", 12345),
        "headers": [(b"origin", ORIGIN.encode()), (b"x-request-id", REQUEST_ID.encode()),
                    (b"content-type", b"image/png")],
    }, receive, send)
    return httpx.Response(sent[0]["status"], headers=sent[0]["headers"],
                          content=b"".join(m.get("body", b"") for m in sent[1:]))


async def test_body_timeout_keeps_shared_error_headers(app_factory):
    async def stalled_receive():
        await asyncio.Event().wait()

    response = await request_asgi(app_factory(read_timeout=0.01), stalled_receive)
    assert_error(response, 408, "request_timeout", "Image upload request timed out")


async def test_busy_capacity_keeps_shared_error_headers_and_retry_after(app_factory):
    app = app_factory(max_inflight=1)
    entered = asyncio.Event()

    async def stalled_receive():
        entered.set()
        await asyncio.Event().wait()

    async def unexpected_receive():
        raise AssertionError("Busy admission must not consume the request body")

    first = asyncio.create_task(request_asgi(app, stalled_receive))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        response = await request_asgi(app, unexpected_receive)
        assert_error(response, 503, "service_unavailable", "Image upload capacity is busy")
        assert response.headers["retry-after"] == "1"
    finally:
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first


def test_production_retains_existing_server_timing_privacy_policy(app_factory, monkeypatch):
    client = TestClient(app_factory(environment="production"))
    try:
        response = oversized(client)
        assert response.status_code == 413
        assert response.headers["access-control-allow-origin"] == ORIGIN
        assert response.headers["x-request-id"] == REQUEST_ID
        assert "server-timing" not in response.headers
    finally:
        client.close()


def test_successful_signed_upload_keeps_204_and_family_response(app_factory, monkeypatch):
    app = app_factory()
    storage = gateway()
    storage._client = FakeR2Client()
    monkeypatch.setattr(settings, "r2_bucket", "images")
    app.dependency_overrides[get_current_actor] = lambda: make_profile()
    app.dependency_overrides[get_authenticated_session] = lambda: None
    app.dependency_overrides[get_storage_gateway] = lambda: storage
    client = TestClient(app)
    try:
        grant_response = client.post("/v1/profiles/me/avatar-upload-url", json={
            "filename": "synthetic.jpg", "content_type": "image/jpeg",
        })
        assert grant_response.status_code == 200
        grant = grant_response.json()
        path = urlsplit(grant["upload_url"]).path
        response = client.put(path, content=photo_data, headers={
            "Content-Type": "image/jpeg", "Origin": ORIGIN, "X-Request-ID": REQUEST_ID,
        })
        assert response.status_code == 204
        assert response.content == b""
        assert response.headers["access-control-allow-origin"] == ORIGIN
        assert response.headers["x-request-id"] == REQUEST_ID
        assert "app;dur=" in response.headers["server-timing"]
        assert grant["result_url"] != grant["upload_url"]
        result = client.get(urlsplit(grant["result_url"]).path).json()
        assert response.headers["x-image-family-id"] == result["family_id"]
        assert result["public_url"] == grant["public_url"]
        assert set(result["variants"]) == {"avatar"}
        assert all(o["ContentType"] == "image/webp" for o in storage._client.objects.values())
    finally:
        client.close()
