"""Payment settings HTTP contract: routes exist, only a super admin gets in, bodies are strict."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.payment_settings import PaymentSettingsUpdate, SalonCommissionUpdate
from app.domain.entities.profile import Role
from app.main import app
from tests.conftest import make_profile

SALON_ID = "11111111-1111-4111-8111-111111111111"
ROUTES = [
    ("GET", "/v1/admin/payment-settings"),
    ("PUT", "/v1/admin/payment-settings"),
    ("GET", f"/v1/admin/salons/{SALON_ID}/commission-rate"),
    ("PUT", f"/v1/admin/salons/{SALON_ID}/commission-rate"),
    ("DELETE", f"/v1/admin/salons/{SALON_ID}/commission-rate"),
]


def _body(method: str, path: str):
    if method != "PUT":
        return None
    if path.endswith("payment-settings"):
        return {"commission_rate_percent": "10", "commission_base": "online_amount", "min_payout_paise": 10000}
    return {"commission_rate_percent": "5"}


def test_routes_are_in_the_openapi_contract():
    paths = app.openapi()["paths"]
    for method, path in ROUTES:
        assert method.lower() in paths[path.replace(SALON_ID, "{salon_id}")], path


@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_no_anonymous_access(method, path):
    assert TestClient(app).request(method, path, json=_body(method, path)).status_code == 401


@pytest.mark.parametrize(("method", "path"), ROUTES)
@pytest.mark.parametrize("role", [Role.owner, Role.staff, Role.customer])
def test_every_other_role_is_refused(method, path, role):
    async def session():
        yield None

    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=role)
    app.dependency_overrides[get_authenticated_session] = session
    try:
        assert TestClient(app).request(method, path, json=_body(method, path)).status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "values",
    [
        {"commission_rate_percent": "101", "commission_base": "online_amount", "min_payout_paise": 10000},
        {"commission_rate_percent": "-1", "commission_base": "online_amount", "min_payout_paise": 10000},
        {"commission_rate_percent": "1.234", "commission_base": "online_amount", "min_payout_paise": 10000},
        {"commission_rate_percent": "10", "commission_base": "everything", "min_payout_paise": 10000},
        {"commission_rate_percent": "10", "commission_base": "online_amount", "min_payout_paise": 99},
        {"commission_rate_percent": "10", "commission_base": "online_amount", "min_payout_paise": 100_000_001},
        {"commission_rate_percent": "10", "commission_base": "online_amount", "min_payout_paise": 10000.5},
        {"commission_rate_percent": "10", "commission_base": "online_amount", "min_payout_paise": 10000, "x": 1},
        {"commission_rate_percent": "10", "commission_base": "online_amount"},
        {"min_payout_paise": 10000},  # leaving the rate and base out must not clear them
    ],
)
def test_settings_body_is_strict(values):
    with pytest.raises(ValidationError):
        PaymentSettingsUpdate(**values)


def test_rate_and_base_can_both_be_cleared():
    body = PaymentSettingsUpdate(commission_rate_percent=None, commission_base=None, min_payout_paise=10000)
    assert body.commission_rate_percent is None and body.commission_base is None


@pytest.mark.parametrize("values", [{"commission_rate_percent": "101"}, {"commission_rate_percent": "5", "note": "x" * 201},
                                    {"commission_rate_percent": "5", "extra": 1}, {}])
def test_salon_rate_body_is_strict(values):
    with pytest.raises(ValidationError):
        SalonCommissionUpdate(**values)
