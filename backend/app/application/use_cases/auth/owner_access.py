"""Self-service salon-owner access use case."""

from app.application.dto.auth import MeOutput
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Profile, Role
from app.domain.repositories.profile_repository import ProfileRepository
from app.domain.services.authorization import require_active


class EnsureOwnerAccess:
    """Give any authenticated Google account access to the salon workspace.

    Signing in is self-service: there is no super-admin allocation step in front of the
    owner app, so whoever signs in owns their own salon. Supabase's ``handle_new_user``
    trigger lands every new user on ``role = 'customer'`` (that default belongs to the
    customer surface and is deliberately left alone), so the owner app calls this once at
    sign-in to claim the workspace role. The salon row itself is still created lazily by
    ``OwnerUseCases.complete_profile`` at the end of onboarding.

    Idempotent by design — it is safe on every sign-in:
      - ``customer``    → promoted to ``owner``
      - ``owner``       → returned unchanged
      - ``staff``       → returned unchanged; they already have workspace access, and
                          promoting them would silently detach them from their salon
      - ``super_admin`` → returned unchanged; never demoted into an owner
    """

    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    async def execute(self, actor: Profile) -> MeOutput:
        """Return the actor holding a salon-workspace role, promoting them if needed."""

        require_active(actor)

        if actor.role != Role.customer:
            return MeOutput(profile=actor)

        promoted = await self.repository.grant_owner_role(actor.id)
        if promoted is None:
            # The row was deactivated or its role changed between the two statements —
            # rare, but never report success for a profile we did not actually promote.
            raise ForbiddenError("Could not grant salon workspace access")
        return MeOutput(profile=promoted)
