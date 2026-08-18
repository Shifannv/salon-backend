"""Profile repository port."""

from typing import Protocol

from app.domain.entities.profile import Profile


class ProfileRepository(Protocol):
    """Persistence port for profile lookups."""

    async def get_by_id(self, profile_id: str) -> Profile | None:
        """Return an active or inactive profile by identifier."""

    async def grant_owner_role(self, profile_id: str) -> Profile | None:
        """Promote an active ``customer`` profile to ``owner`` and return it.

        Returns ``None`` when no row was promoted — the profile is inactive, gone,
        or already holds a non-customer role. Callers decide what that means.
        """
