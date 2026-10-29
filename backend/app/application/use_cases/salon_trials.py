"""Super-admin trial adjustments; owner clients only read their own access state."""

from typing import Any, Protocol

from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_super_admin
from app.domain.services.trial_limits import TrialLimits


class TrialRepository(Protocol):
    async def get_trial(self, salon_id: str) -> dict[str, Any]: ...

    async def update_trial(
        self, salon_id: str, limits: TrialLimits, actor_id: str
    ) -> dict[str, Any]: ...


class SalonTrialUseCases:
    def __init__(self, repository: TrialRepository) -> None:
        self.repository = repository

    async def get(self, actor: Profile, salon_id: str) -> dict[str, Any]:
        require_super_admin(actor)
        return await self.repository.get_trial(salon_id)

    async def update(
        self, actor: Profile, salon_id: str, limits: TrialLimits
    ) -> dict[str, Any]:
        require_super_admin(actor)
        return await self.repository.update_trial(salon_id, limits, str(actor.id))
