import pytest

from app.application.use_cases.auth.me import GetMe
from app.application.use_cases.auth.owner_access import EnsureOwnerAccess
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Profile, Role


def _profile(role: Role = Role.customer, is_active: bool = True) -> Profile:
    return Profile(
        id="00000000-0000-0000-0000-000000000001",
        role=role,
        full_name="Test User",
        email="test@example.com",
        phone=None,
        phone_verified=False,
        avatar_url=None,
        is_active=is_active,
    )


class FakeProfileRepository:
    """Records promotion calls and returns whatever the test wants back."""

    def __init__(self, promoted: Profile | None) -> None:
        self.promoted = promoted
        self.calls: list[str] = []

    async def get_by_id(self, profile_id: str) -> Profile | None:
        raise AssertionError("not used by these tests")

    async def grant_owner_role(self, profile_id: str) -> Profile | None:
        self.calls.append(profile_id)
        return self.promoted


async def test_get_me_returns_active_actor() -> None:
    actor = _profile()

    response = await GetMe().execute(actor)

    assert response.profile == actor


async def test_owner_access_promotes_a_new_google_account() -> None:
    """Any Google account may sign in; the first owner-app call claims the owner role."""

    actor = _profile(role=Role.customer)
    repository = FakeProfileRepository(promoted=_profile(role=Role.owner))

    response = await EnsureOwnerAccess(repository).execute(actor)

    assert response.profile.role is Role.owner
    assert repository.calls == [actor.id]


@pytest.mark.parametrize("role", [Role.owner, Role.staff, Role.super_admin])
async def test_owner_access_leaves_workspace_roles_untouched(role: Role) -> None:
    """Idempotent on every sign-in: no write, and no super admin demoted into an owner."""

    actor = _profile(role=role)
    repository = FakeProfileRepository(promoted=None)

    response = await EnsureOwnerAccess(repository).execute(actor)

    assert response.profile == actor
    assert repository.calls == []


async def test_owner_access_rejects_an_inactive_account() -> None:
    repository = FakeProfileRepository(promoted=None)

    with pytest.raises(ForbiddenError):
        await EnsureOwnerAccess(repository).execute(_profile(is_active=False))

    assert repository.calls == []


async def test_owner_access_fails_when_the_promotion_matches_no_row() -> None:
    """A profile deactivated mid-request must not come back reported as an owner."""

    repository = FakeProfileRepository(promoted=None)

    with pytest.raises(ForbiddenError):
        await EnsureOwnerAccess(repository).execute(_profile(role=Role.customer))
