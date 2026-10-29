from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.admin import AdminApproveSalonRequest
from app.api.v1.schemas.trial import TrialLimitsRequest, TrialUpdateRequest
from app.application.use_cases.admin import AdminUseCases
from app.application.use_cases.salon_trials import SalonTrialUseCases
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Role
from app.domain.services.trial_limits import TrialLimits
from app.main import app
from tests.conftest import make_mock_repo, make_profile, make_super_admin

SALON = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize("role", [Role.owner, Role.customer, Role.staff])
async def test_non_admin_cannot_read_or_modify_trial(role):
    repo = AsyncMock()
    uc = SalonTrialUseCases(repo)
    for method, args in [(uc.get, ()), (uc.update, (TrialLimits(30, 75),))]:
        with pytest.raises(ForbiddenError):
            await method(make_profile(role=role), SALON, *args)
    repo.get_trial.assert_not_awaited()
    repo.update_trial.assert_not_awaited()


async def test_trial_update_uses_verified_admin_and_target_salon():
    repo = AsyncMock()
    limits = TrialLimits(30, 75)
    await SalonTrialUseCases(repo).update(make_super_admin(), SALON, limits)
    repo.update_trial.assert_awaited_once_with(SALON, limits, "admin-001")


async def test_custom_trial_limits_join_the_approval_transaction():
    repo = make_mock_repo()
    repo.admin_get_salon.return_value = {"is_active": True, "profile_completed": True}
    limits = TrialLimits(14, 50)
    await AdminUseCases(repo, object()).approve_salon(
        make_super_admin(), SALON, trial_limits=limits
    )
    repo.admin_set_salon_approval.assert_awaited_once_with(
        SALON, "approved", "admin-001", None, trial_limits=limits
    )


@pytest.mark.parametrize("schema", [TrialLimitsRequest, AdminApproveSalonRequest])
@pytest.mark.parametrize("values", [
    {"trial_days": 0}, {"trial_days": 3651}, {"trial_days": True},
    {"trial_days": "30"}, {"trial_booking_limit": 0},
    {"trial_booking_limit": 1_000_001}, {"trial_booking_limit": 2.5},
    {"trial_booking_limit": False}, {"owner_id": SALON},
])
def test_trial_inputs_reject_invalid_or_owner_supplied_fields(schema, values):
    with pytest.raises(ValidationError):
        schema(**values)


def test_empty_approval_body_retains_the_current_default_trial():
    value = AdminApproveSalonRequest()
    assert value.trial_days == 60
    assert value.trial_booking_limit == 500


@pytest.mark.parametrize("values", [{}, {"trial_days": 30}, {"trial_booking_limit": 75}])
def test_trial_update_requires_both_limits_without_implicit_resets(values):
    with pytest.raises(ValidationError):
        TrialUpdateRequest(**values)


@pytest.mark.parametrize("method", ["GET", "PUT"])
@pytest.mark.parametrize("role", [Role.owner, Role.customer, Role.staff])
def test_trial_http_routes_reject_other_roles_before_repository_access(method, role):
    async def session():
        yield None

    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=role)
    app.dependency_overrides[get_authenticated_session] = session
    try:
        response = TestClient(app).request(method, f"/v1/admin/salons/{SALON}/trial",
                                          json={"trial_days": 30, "trial_booking_limit": 75})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_trial_http_response_and_no_anonymous_access(monkeypatch):
    assert TestClient(app).get(f"/v1/admin/salons/{SALON}/trial").status_code == 401
    repo = AsyncMock()
    repo.get_trial.return_value = {
        "salon_id": SALON, "trial_days": 30, "trial_booking_limit": 75,
        "bookings_counted": 7, "trial_started_at": datetime(2026, 10, 1, tzinfo=UTC),
        "trial_ends_at": datetime(2026, 10, 31, tzinfo=UTC), "state": "active",
    }
    monkeypatch.setattr("app.api.v1.routes.subscriptions.SalonTrialRepository", lambda _: repo)

    async def session():
        yield None

    app.dependency_overrides[get_current_actor] = make_super_admin
    app.dependency_overrides[get_authenticated_session] = session
    try:
        response = TestClient(app).get(f"/v1/admin/salons/{SALON}/trial")
        assert response.status_code == 200
        assert response.json()["trial_booking_limit"] == 75
        assert response.json()["bookings_counted"] == 7
    finally:
        app.dependency_overrides.clear()
