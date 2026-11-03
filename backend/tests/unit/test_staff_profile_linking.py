"""An owner may link a staff row only to an unused staff login, never to an arbitrary account."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ValidationError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

PROFILE = "11111111-1111-4111-8111-111111111111"
SALON = {"id": "22222222-2222-4222-8222-222222222222"}


def repo_with_profile_row(row):
    session = MagicMock()
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    result.mappings.return_value.one.return_value = {
        "id": "s1", "salon_id": SALON["id"], "profile_id": PROFILE, "name": "A",
        "photo_url": None, "specialization": None, "experience": None, "working_hours": None,
        "is_active": True, "created_at": None, "updated_at": None,
    }
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return PlatformRepository(session), session


@pytest.mark.parametrize("row", [
    None,
    {"role": "customer", "used_elsewhere": False},
    {"role": "owner", "used_elsewhere": False},
    {"role": "super_admin", "used_elsewhere": False},
    {"role": "staff", "used_elsewhere": True},
])
async def test_create_refuses_accounts_that_are_not_free_staff_logins(row):
    repo, session = repo_with_profile_row(row)
    with (
        patch.object(PlatformRepository, "get_owner_salon", AsyncMock(return_value=SALON)),
        pytest.raises(ValidationError),
    ):
        await repo.create_owner_staff("owner-1", {"name": "A", "profile_id": PROFILE})
    session.commit.assert_not_awaited()


async def test_update_refuses_a_non_staff_account():
    repo, session = repo_with_profile_row({"role": "customer", "used_elsewhere": False})
    with (
        patch.object(PlatformRepository, "get_owner_salon", AsyncMock(return_value=SALON)),
        pytest.raises(ValidationError),
    ):
        await repo.update_owner_staff("owner-1", "s1", {"profile_id": PROFILE})
    session.commit.assert_not_awaited()


async def test_malformed_profile_id_is_refused_without_a_query():
    repo, session = repo_with_profile_row(None)
    with (
        patch.object(PlatformRepository, "get_owner_salon", AsyncMock(return_value=SALON)),
        pytest.raises(ValidationError),
    ):
        await repo.create_owner_staff("owner-1", {"name": "A", "profile_id": "not-a-uuid'; --"})
    session.execute.assert_not_awaited()


async def test_free_staff_login_can_be_linked():
    repo, session = repo_with_profile_row({"role": "staff", "used_elsewhere": False})
    with patch.object(PlatformRepository, "get_owner_salon", AsyncMock(return_value=SALON)):
        created = await repo.create_owner_staff("owner-1", {"name": "A", "profile_id": PROFILE})
    assert created["profile_id"] == PROFILE
    session.commit.assert_awaited_once()


async def test_staff_without_a_login_is_unaffected():
    repo, session = repo_with_profile_row(None)
    with patch.object(PlatformRepository, "get_owner_salon", AsyncMock(return_value=SALON)):
        created = await repo.create_owner_staff("owner-1", {"name": "A"})
    assert created["name"] == "A"
    assert session.execute.await_count == 1
