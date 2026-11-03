"""Admin MFA uses verified claims and the database role."""

from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from app.api.deps import get_current_actor, require_role
from app.core.config import settings
from app.core.exceptions import AdminMFARequiredError, ForbiddenError
from app.domain.entities.profile import Role
from tests.conftest import make_profile, make_super_admin


@pytest.mark.asyncio
@pytest.mark.parametrize("aal", [None, "aal1", "aal2"])
async def test_admin_mfa_gate_fails_closed_without_verified_second_factor(monkeypatch, aal):
    monkeypatch.setattr(settings, "admin_require_mfa", True)
    request = Request({"type": "http"})
    request.state.verified_auth_claims = {"aal": aal}
    gate = require_role(Role.super_admin)
    if aal == "aal2":
        assert (await gate(request, make_super_admin())).role == Role.super_admin
    else:
        with pytest.raises(AdminMFARequiredError):
            await gate(request, make_super_admin())


@pytest.mark.asyncio
async def test_second_factor_does_not_grant_admin_role(monkeypatch):
    monkeypatch.setattr(settings, "admin_require_mfa", True)
    request = Request({"type": "http"})
    request.state.verified_auth_claims = {"aal": "aal2", "role": "super_admin"}
    with pytest.raises(ForbiddenError):
        await require_role(Role.super_admin)(request, make_profile())


@pytest.mark.asyncio
async def test_actor_uses_verified_subject_and_database_role():
    from fastapi.security import HTTPAuthorizationCredentials

    request = Request({"type": "http"})
    claims = {"sub": "customer-id", "aal": "aal2", "role": "super_admin"}
    repo = AsyncMock()
    repo.get_by_id.return_value = make_profile(id="customer-id", role=Role.customer)
    with (
        patch("app.api.deps._jwt_verifier.verify_claims", AsyncMock(return_value=claims)),
        patch("app.api.deps.SQLProfileRepository", return_value=repo),
    ):
        actor = await get_current_actor(request, HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="opaque-token"), AsyncMock())
    repo.get_by_id.assert_awaited_once_with("customer-id")
    assert actor.role == Role.customer
    assert request.state.verified_auth_claims == claims


@pytest.mark.asyncio
@pytest.mark.parametrize("aal", [None, "aal1"])
async def test_shared_routes_also_require_the_second_factor_for_super_admin(monkeypatch, aal):
    from app.api.deps import get_mfa_checked_actor

    monkeypatch.setattr(settings, "admin_require_mfa", True)
    request = Request({"type": "http"})
    request.state.verified_auth_claims = {"aal": aal}
    with pytest.raises(AdminMFARequiredError):
        await get_mfa_checked_actor(request, make_super_admin())


@pytest.mark.asyncio
async def test_shared_routes_do_not_change_for_other_roles_or_with_a_second_factor(monkeypatch):
    from app.api.deps import get_mfa_checked_actor

    monkeypatch.setattr(settings, "admin_require_mfa", True)
    request = Request({"type": "http"})
    request.state.verified_auth_claims = {"aal": "aal1"}
    customer = make_profile()
    assert await get_mfa_checked_actor(request, customer) is customer
    request.state.verified_auth_claims = {"aal": "aal2"}
    admin = make_super_admin()
    assert await get_mfa_checked_actor(request, admin) is admin
    monkeypatch.setattr(settings, "admin_require_mfa", False)
    request.state.verified_auth_claims = {"aal": None}
    assert await get_mfa_checked_actor(request, admin) is admin
