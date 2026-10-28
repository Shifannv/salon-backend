"""Approval authorization, workspace gates, and HTTP contracts."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_auth_admin_gateway,
    get_authenticated_session,
    get_cache,
    get_current_actor,
)
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
async def test_super_admin_reactivates_salon_and_unbans_owner_before_database_activation():
    repo = make_mock_repo()
    repo.admin_get_salon.return_value = {
        "id": "salon-001",
        "owner_id": "owner-001",
        "is_active": False,
    }
    repo.admin_reactivate_salon = AsyncMock(
        return_value={"id": "salon-001", "owner_id": "owner-001", "is_active": True}
    )
    gateway = AsyncMock()

    result = await AdminUseCases(repo, gateway).reactivate_salon(
        make_super_admin(), "salon-001"
    )

    assert result["is_active"] is True
    gateway.unban_user.assert_awaited_once_with("owner-001")
    repo.admin_reactivate_salon.assert_awaited_once_with("salon-001")


@pytest.mark.asyncio
async def test_non_admin_cannot_reactivate_salon():
    repo = make_mock_repo()
    repo.admin_reactivate_salon = AsyncMock()
    gateway = AsyncMock()

    with pytest.raises(ForbiddenError):
        await AdminUseCases(repo, gateway).reactivate_salon(
            make_profile(role=Role.owner), "salon-001"
        )

    gateway.unban_user.assert_not_awaited()
    repo.admin_reactivate_salon.assert_not_awaited()


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
        for suffix, body in [
            ("approve", None),
            ("reject", {"rejection_reason": "Fix setup"}),
            ("reactivate", None),
        ]:
            response = client.post(f"{path}/{suffix}", json=body)
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_reactivate_http_contract_returns_salon_and_invalidates_public_caches():
    from unittest.mock import patch

    async def session():
        yield object()

    salon = {
        "id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "00000000-0000-0000-0000-000000000002",
        "name": "Salon",
        "timezone": "UTC",
        "approval_mode": "auto",
        "profile_completed": False,
        "is_active": True,
        "approval_status": "pending",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    use_cases = AsyncMock()
    use_cases.reactivate_salon.return_value = salon
    cache = AsyncMock()
    app.dependency_overrides[get_current_actor] = lambda: make_super_admin()
    app.dependency_overrides[get_authenticated_session] = session
    app.dependency_overrides[get_auth_admin_gateway] = lambda: object()
    app.dependency_overrides[get_cache] = lambda: cache
    try:
        with patch("app.api.v1.routes.admin._admin_use_cases", return_value=use_cases):
            response = TestClient(app).post(
                "/v1/admin/salons/00000000-0000-0000-0000-000000000001/reactivate"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    cache.delete_prefix.assert_any_await("salon:00000000-0000-0000-0000-000000000001:")
    cache.delete_prefix.assert_any_await("walkin:qr:")


def test_owner_salon_response_exposes_approved_at_for_the_verified_celebration():
    from datetime import UTC, datetime

    from app.api.v1.schemas.platform import OwnerSalonResponse

    base = {
        "id": "s",
        "owner_id": "o",
        "name": "Salon",
        "timezone": "UTC",
        "working_hours": {},
        "approval_mode": "auto",
        "accepting_bookings": True,
        "slot_interval_minutes": 30,
        "qr_token": "q",
        "profile_completed": True,
        "approval_status": "approved",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    stamped = datetime(2026, 2, 3, 4, 5, tzinfo=UTC)
    assert (
        OwnerSalonResponse(**base, approved_at=stamped)
        .model_dump(mode="json")["approved_at"]
        .startswith("2026-02-03T04:05")
    )
    assert OwnerSalonResponse(**base).model_dump()["approved_at"] is None
