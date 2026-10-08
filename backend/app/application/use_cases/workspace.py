"""Shared application authorization for daily salon operations."""

from app.application.ports.salon_approval_repository import WorkspaceRepository
from app.core.exceptions import ForbiddenError, SalonApprovalRequiredError
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import is_owner_or_staff


async def assert_approved_workspace(
    repository: WorkspaceRepository, actor: Profile
) -> None:
    if not is_owner_or_staff(actor):
        raise ForbiddenError("Salon workspace access required")
    if actor.role == Role.super_admin:
        return
    salon = await repository.get_workspace_salon(actor.id)
    if not salon or not salon["is_active"]:
        raise ForbiddenError("Active salon workspace required")
    if not salon["profile_completed"] or salon["approval_status"] != "approved":
        raise SalonApprovalRequiredError("Super admin approval is required for daily business")
