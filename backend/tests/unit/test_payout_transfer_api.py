"""Automatic payout HTTP contract: routes exist, only a super admin with MFA gets in, the webhook is signed."""

import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.routes import payout_transfer
from app.core.config import Settings
from app.domain.entities.profile import Role
from app.infrastructure.db.session import get_session
from app.infrastructure.payouts.cashfree import CashfreePayoutGateway
from app.main import app
from tests.conftest import make_profile

REQUEST_ID = "22222222-2222-4222-8222-222222222222"
SECRET = "payout_webhook_secret_for_tests"
ROUTES = [
    f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/send-transfer",
    f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/transfer/refresh",
]
WEBHOOK = "/v1/webhooks/payouts/cashfree"


async def _no_session():
    yield None


def _gateway() -> CashfreePayoutGateway:
    settings = Settings(
        _env_file=None, environment="test", payout_provider="cashfree",
        cashfree_payout_client_id="pid", cashfree_payout_client_secret=SECRET,
    )
    return CashfreePayoutGateway(settings, httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))


def _signed(body: bytes, *, secret: str = SECRET) -> dict[str, str]:
    stamp = str(int(time.time()))
    digest = hmac.new(secret.encode(), stamp.encode() + body, hashlib.sha256).digest()
    return {"x-webhook-timestamp": stamp, "x-webhook-signature": base64.b64encode(digest).decode(),
            "content-type": "application/json"}


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


def test_routes_are_in_the_openapi_contract_with_explicit_statuses():
    paths = app.openapi()["paths"]
    send = paths[ROUTES[0].replace(REQUEST_ID, "{request_id}")]["post"]
    refresh = paths[ROUTES[1].replace(REQUEST_ID, "{request_id}")]["post"]
    assert "202" in send["responses"] and "200" in refresh["responses"]
    assert "post" in paths["/v1/webhooks/payouts/{provider}"]


@pytest.mark.parametrize("path", ROUTES)
def test_no_anonymous_access(path):
    assert TestClient(app).post(path).status_code == 401


@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("role", [Role.owner, Role.staff, Role.customer])
def test_every_other_role_is_refused(path, role):
    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=role)
    app.dependency_overrides[get_authenticated_session] = _no_session
    assert TestClient(app).post(path).status_code == 403


@pytest.mark.parametrize("path", ROUTES)
def test_a_super_admin_without_the_second_factor_is_refused(path, monkeypatch):
    monkeypatch.setattr(deps.settings, "admin_require_mfa", True)
    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=Role.super_admin)
    app.dependency_overrides[get_authenticated_session] = _no_session
    app.dependency_overrides[payout_transfer.get_payout_gateway] = _gateway
    response = TestClient(app).post(path)
    assert response.status_code == 403 and response.json()["error"]["code"] == "mfa_required"


@pytest.mark.parametrize("path", ROUTES)
def test_without_a_configured_provider_the_admin_is_told_to_pay_by_hand(path, monkeypatch):
    monkeypatch.setattr(deps.settings, "admin_require_mfa", False)
    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=Role.super_admin)
    app.dependency_overrides[get_authenticated_session] = _no_session
    app.dependency_overrides[payout_transfer.get_payout_gateway] = lambda: None
    response = TestClient(app).post(path)
    assert response.status_code == 503 and response.json()["error"]["code"] == "payout_provider_unavailable"


def test_a_forged_webhook_is_refused_and_changes_nothing(monkeypatch):
    applied = []

    class Spy:
        async def apply(self, result, *, admin_id):
            applied.append(result)

    monkeypatch.setattr(payout_transfer, "_use_cases", lambda session, gateway: Spy())
    app.dependency_overrides[get_session] = _no_session
    app.dependency_overrides[payout_transfer.get_payout_gateway] = _gateway
    body = json.dumps({"type": "TRANSFER_SUCCESS", "data": {"transfer_id": "po_1", "status": "SUCCESS"}}).encode()

    forged = TestClient(app).post(WEBHOOK, content=body, headers=_signed(body, secret="evil"))
    unsigned = TestClient(app).post(WEBHOOK, content=body)

    assert forged.status_code == 400 and forged.json()["error"]["code"] == "invalid_webhook_signature"
    assert unsigned.status_code == 400
    assert applied == []


def test_a_signed_event_is_applied_and_an_unrelated_one_is_acknowledged_and_ignored(monkeypatch):
    applied = []

    class Spy:
        async def apply(self, result, *, admin_id):
            applied.append((result.transfer_id, result.status, admin_id))

    monkeypatch.setattr(payout_transfer, "_use_cases", lambda session, gateway: Spy())
    app.dependency_overrides[get_session] = _no_session
    app.dependency_overrides[payout_transfer.get_payout_gateway] = _gateway
    ok = json.dumps({"type": "TRANSFER_SUCCESS", "data": {"transfer_id": "po_1", "status": "SUCCESS"}}).encode()
    other = json.dumps({"type": "BENEFICIARY_INCIDENT", "data": {}}).encode()

    accepted = TestClient(app).post(WEBHOOK, content=ok, headers=_signed(ok))
    ignored = TestClient(app).post(WEBHOOK, content=other, headers=_signed(other))

    assert accepted.json() == {"status": "accepted"} and ignored.json() == {"status": "ignored"}
    assert applied == [("po_1", "SUCCESS", None)]  # a provider event has no admin


def test_the_webhook_is_refused_when_payouts_are_not_configured(monkeypatch):
    app.dependency_overrides[get_session] = _no_session
    app.dependency_overrides[payout_transfer.get_payout_gateway] = lambda: None
    response = TestClient(app).post(WEBHOOK, content=b"{}")
    assert response.status_code == 503 and response.json()["error"]["code"] == "payout_provider_unavailable"


def test_a_webhook_for_another_provider_name_is_not_found(monkeypatch):
    app.dependency_overrides[get_session] = _no_session
    app.dependency_overrides[payout_transfer.get_payout_gateway] = _gateway
    response = TestClient(app).post("/v1/webhooks/payouts/other", content=b"{}")
    assert response.status_code == 404


def test_an_oversized_webhook_is_refused_before_it_is_read(monkeypatch):
    monkeypatch.setattr(payout_transfer.settings, "payment_webhook_max_body_bytes", 1024)
    app.dependency_overrides[get_session] = _no_session
    app.dependency_overrides[payout_transfer.get_payout_gateway] = _gateway
    response = TestClient(app).post(WEBHOOK, content=b"x" * 2048, headers=_signed(b"x" * 2048))
    assert response.status_code == 413
