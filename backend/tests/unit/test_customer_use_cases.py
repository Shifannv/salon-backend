"""Unit tests for CustomerUseCases."""

from uuid import uuid4

import pytest

from app.application.use_cases.platform import CustomerUseCases
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Role
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from tests.conftest import make_mock_repo, make_owner, make_profile


@pytest.mark.asyncio
async def test_update_profile_allows_customer() -> None:
    repo = make_mock_repo()
    repo.update_profile.return_value = {"id": "customer-001", "phone": "+919009908978"}
    uc = CustomerUseCases(repo)
    actor = make_profile(role=Role.customer)

    profile = await uc.update_profile(actor, {"phone": "+919009908978"})

    assert profile["phone"] == "+919009908978"
    repo.update_profile.assert_awaited_once_with(actor.id, {"phone": "+919009908978"})


@pytest.mark.asyncio
async def test_update_profile_allows_owner_personal_profile() -> None:
    repo = make_mock_repo()
    repo.update_profile.return_value = {"id": "owner-001", "phone": "+919009908978"}
    uc = CustomerUseCases(repo)
    actor = make_owner()

    profile = await uc.update_profile(actor, {"phone": "+919009908978"})

    assert profile["phone"] == "+919009908978"
    repo.update_profile.assert_awaited_once_with(actor.id, {"phone": "+919009908978"})


@pytest.mark.asyncio
async def test_update_profile_rejects_staff_customer_surface() -> None:
    repo = make_mock_repo()
    uc = CustomerUseCases(repo)
    actor = make_profile(role=Role.staff)

    with pytest.raises(ForbiddenError):
        await uc.update_profile(actor, {"phone": "+919009908978"})


def test_profile_response_normalizes_uuid_id_for_api_schema() -> None:
    repo = PlatformRepository(session=object())
    profile_id = uuid4()

    profile = repo._profile_response({
        "id": profile_id,
        "role": "owner",
        "full_name": "Thameem Pp",
        "email": None,
        "phone": "+919009908978",
        "phone_verified": False,
        "avatar_url": "",
        "is_active": True,
    })

    assert profile["id"] == str(profile_id)
