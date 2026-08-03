"""Current-profile use case."""

from app.application.dto.auth import MeOutput
from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_active


class GetMe:
    """Return the authenticated profile."""

    async def execute(self, actor: Profile) -> MeOutput:
        """Return the actor profile after domain-level active-account validation."""

        require_active(actor)
        return MeOutput(profile=actor)
