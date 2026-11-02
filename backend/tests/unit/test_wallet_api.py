"""Wallet HTTP contract: routes exist, auth is enforced, request bodies are strict."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.wallet import (
    PayoutRejectRequest,
    PayoutRequestCreate,
)
from app.domain.entities.profile import Role
from app.main import app
from tests.conftest import make_profile

REQUEST_ID = "22222222-2222-4222-8222-222222222222"
OWNER_ROUTES = [
    ("GET", "/v1/salons/me/wallet"),
    ("GET", "/v1/salons/me/wallet/entries"),
    ("POST", "/v1/salons/me/wallet/payout-requests"),
    ("POST", f"/v1/salons/me/wallet/payout-requests/{REQUEST_ID}/cancel"),
]
ADMIN_ROUTES = [
    ("GET", "/v1/admin/wallet/payout-requests"),
    ("GET", f"/v1/admin/wallet/payout-requests/{REQUEST_ID}"),
    ("GET", f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/proof"),
    ("POST", f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/mark-paid"),
    ("POST", f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/corrections"),
    ("GET", f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/corrections/{REQUEST_ID}/proof"),
    ("GET", "/v1/admin/wallet/payout-reconciliation?from=2026-11-01&to=2026-11-02"),
    ("POST", f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/reject"),
    ("POST", f"/v1/admin/wallet/payout-requests/{REQUEST_ID}/reveal-account"),
]
BODIES = {
    "payout-requests": {"amount_paise": 100000, "scheduled_for": "2026-11-02"},
    "mark-paid": {"reference": "1234"},
    "reject": {"reason": "Account name did not match"},
}


def _body(path: str):
    return next((body for tail, body in BODIES.items() if path.endswith(tail)), None)


def test_wallet_routes_are_in_the_openapi_contract():
    paths = app.openapi()["paths"]
    for method, path in OWNER_ROUTES + ADMIN_ROUTES:
        template = path.split("?")[0].replace(f"requests/{REQUEST_ID}/corrections/{REQUEST_ID}", "requests/{request_id}/corrections/{correction_id}")
        template = template.replace(REQUEST_ID, "{request_id}")
        assert method.lower() in paths[template], template


@pytest.mark.parametrize(("method", "path"), OWNER_ROUTES + ADMIN_ROUTES)
def test_no_anonymous_access(method, path):
    assert TestClient(app).request(method, path, json=_body(path)).status_code == 401


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
@pytest.mark.parametrize("role", [Role.owner, Role.staff, Role.customer])
def test_admin_payout_routes_reject_every_other_role(method, path, role):
    async def session():
        yield None

    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=role)
    app.dependency_overrides[get_authenticated_session] = session
    try:
        assert TestClient(app).request(method, path, json=_body(path)).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_a_payout_request_without_an_idempotency_key_is_refused_before_any_database_work():
    async def session():
        yield None  # any repository call on it would fail loudly

    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=Role.owner)
    app.dependency_overrides[get_authenticated_session] = session
    try:
        response = TestClient(app).post("/v1/salons/me/wallet/payout-requests", json=_body("payout-requests"))
        assert response.status_code in {400, 422}
        assert response.json()["error"]["code"] == "idempotency_key_required"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("values", [
    {}, {"amount_paise": 100000}, {"scheduled_for": "2026-11-02"},
    {"amount_paise": 0, "scheduled_for": "2026-11-02"},
    {"amount_paise": -5, "scheduled_for": "2026-11-02"},
    {"amount_paise": 100.5, "scheduled_for": "2026-11-02"},
    {"amount_paise": "100000", "scheduled_for": "2026-11-02"},
    {"amount_paise": True, "scheduled_for": "2026-11-02"},
    {"amount_paise": 10**13, "scheduled_for": "2026-11-02"},
    {"amount_paise": 100000, "scheduled_for": "not-a-date"},
    {"amount_paise": 100000, "scheduled_for": "2026-11-02", "salon_id": "x"},
    {"amount_paise": 100000, "scheduled_for": "2026-11-02", "available_paise": 99},
])
def test_payout_request_body_is_strict(values):
    with pytest.raises(ValidationError):
        PayoutRequestCreate(**values)


@pytest.mark.parametrize("schema, values", [
    (PayoutRejectRequest, {}), (PayoutRejectRequest, {"reason": "no"}),
    (PayoutRejectRequest, {"reason": "x" * 501}),
])
def test_admin_bodies_are_strict(schema, values):
    with pytest.raises(ValidationError):
        schema(**values)
