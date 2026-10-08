"""Approval authorization, workspace gates, and HTTP contracts."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_auth_admin_gateway, get_authenticated_session, get_current_actor
from app.application.use_cases.admin import AdminUseCases
from app.application.use_cases.booking_actions import BookingActionRequestUseCases, ClosureUseCases
from app.application.use_cases.platform import BookingUseCases, OwnerUseCases
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    SalonApprovalRequiredError,
    ValidationError,
)
from app.domain.entities.profile import Role
from app.main import app
from tests.conftest import make_mock_repo, make_owner, make_profile, make_super_admin


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.customer, Role.owner, Role.staff])
async def test_only_super_admin_can_review(role):
    repo = make_mock_repo()
    uc = AdminUseCases(repo, object())
    for method, args in [(uc.approve_salon, ()), (uc.reject_salon, ("Incomplete address",))]:
        with pytest.raises(ForbiddenError):
            await method(make_profile(role=role), "salon-001", *args)
    repo.admin_set_salon_approval.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("active,complete", [(False, True), (True, False)])
async def test_admin_cannot_approve_inactive_or_incomplete_salon(active, complete):
    repo = make_mock_repo()
    repo.admin_get_salon.return_value = {"is_active": active, "profile_completed": complete}
    with pytest.raises(ConflictError):
        await AdminUseCases(repo, object()).approve_salon(make_super_admin(), "salon-001")
    repo.admin_set_salon_approval.assert_not_awaited()


@pytest.mark.asyncio
async def test_decisions_record_verified_admin_and_trim_reason_without_banning_owner():
    repo = make_mock_repo()
    repo.admin_get_salon.return_value = {"is_active": True, "profile_completed": True}
    gateway = AsyncMock()
    uc = AdminUseCases(repo, gateway)
    await uc.approve_salon(make_super_admin(), "salon-001")
    repo.admin_set_salon_approval.assert_awaited_with("salon-001", "approved", "admin-001", None)
    await uc.reject_salon(make_super_admin(), "salon-001", "  Fix address  ")
    repo.admin_set_salon_approval.assert_awaited_with(
        "salon-001", "rejected", "admin-001", "Fix address"
    )
    with pytest.raises(ValidationError):
        await uc.reject_salon(make_super_admin(), "salon-001", "   ")
    gateway.ban_user.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("approval_status", ["pending", "rejected"])
@pytest.mark.parametrize("role", [Role.owner, Role.staff])
async def test_unapproved_workspace_cannot_run_daily_business(approval_status, role):
    repo = make_mock_repo()
    repo.get_workspace_salon.return_value["approval_status"] = approval_status
    actor = make_profile(role=role)
    operations = [
        (OwnerUseCases(repo).create_holiday, ({"holiday_date": "2030-01-01"},)),
        (OwnerUseCases(repo).list_blocked_slots, ()),
        (OwnerUseCases(repo).get_business_salon, ()),
        (BookingUseCases(repo).list_bookings, ()),
        (BookingUseCases(repo).approve, ("booking-001",)),
        (BookingUseCases(repo).record_payment, ("booking-001", "cash")),
        (BookingUseCases(repo).create_booking, ({"source": "manual_walkin"},)),
        (BookingActionRequestUseCases(repo).list_requests, (None,)),
        (BookingActionRequestUseCases(repo).respond, ("request-001", "received", None)),
    ]
    if role == Role.owner:
        operations += [(ClosureUseCases(repo).apply, ({},))]
    for method, args in operations:
        with pytest.raises(SalonApprovalRequiredError) as exc:
            await method(actor, *args)
        assert exc.value.code == "awaiting_admin_approval"
    repo.create_booking.assert_not_awaited()
    repo.update_booking_status.assert_not_awaited()
    repo.record_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_pending_owner_can_read_status_edit_setup_and_submit_onboarding():
    repo = make_mock_repo()
    pending = {"approval_status": "pending", "profile_completed": True}
    repo.get_owner_salon.return_value = pending
    repo.complete_owner_salon.return_value = pending
    uc = OwnerUseCases(repo)
    assert await uc.get_my_salon(make_owner()) == pending
    await uc.create_staff(make_owner(), {"name": "Barber"})
    assert await uc.complete_profile(make_owner(), {"name": "Salon"}) == pending
    repo.get_workspace_salon.assert_not_awaited()


def test_http_returns_approval_code_for_pending_workspace(monkeypatch):
    repo = make_mock_repo()
    repo.get_workspace_salon.return_value["approval_status"] = "pending"
    monkeypatch.setattr("app.api.v1.routes.owner._use_cases", lambda session: OwnerUseCases(repo))

    async def session():
        yield object()

    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_authenticated_session] = session
    try:
        response = TestClient(app).get("/v1/salons/me/holidays")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "awaiting_admin_approval"
    finally:
        app.dependency_overrides.clear()


def test_admin_approval_routes_enforce_use_case_authorization():
    async def session():
        yield object()

    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_authenticated_session] = session
    app.dependency_overrides[get_auth_admin_gateway] = lambda: object()
    try:
        client = TestClient(app)
        path = "/v1/admin/salons/00000000-0000-0000-0000-000000000001"
        for suffix, body in [("approve", None), ("reject", {"rejection_reason": "Fix setup"})]:
            response = client.post(f"{path}/{suffix}", json=body)
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
