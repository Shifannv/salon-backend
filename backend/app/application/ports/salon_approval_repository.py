"""Persistence operations for salon approval and workspace authorization."""

from typing import Any, Protocol

from app.domain.services.trial_limits import TrialLimits


class WorkspaceRepository(Protocol):
    async def get_workspace_salon(self, actor_id: str) -> dict[str, Any] | None:
        """Read the owner's or assigned staff member's salon without provisioning."""


class SalonApprovalRepository(WorkspaceRepository, Protocol):
    async def admin_get_salon(self, salon_id: str) -> dict[str, Any]: ...

    async def admin_set_salon_approval(
        self, salon_id: str, approval_status: str, actor_id: str, reason: str | None,
        *, trial_limits: TrialLimits | None = None,
    ) -> dict[str, Any]:
        """Atomically decide approval for an active, completed salon."""
