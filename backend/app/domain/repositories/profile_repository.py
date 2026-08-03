"""Profile repository port."""

from typing import Protocol

from app.domain.entities.profile import Profile


class ProfileRepository(Protocol):
    """Persistence port for profile lookups."""

    async def get_by_id(self, profile_id: str) -> Profile | None:
        """Return an active or inactive profile by identifier."""
