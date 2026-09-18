"""Customer salon reports."""

from typing import Protocol

from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Profile, Role


class ReportRepository(Protocol):
    async def get_public_salon(self, salon_id: str) -> dict: ...
    async def create_salon_report(self, actor_id: str, salon_id: str,
                                  reason: str, details: str) -> dict: ...


class SubmitReport:
    def __init__(self, repository: ReportRepository) -> None:
        self.repository = repository

    async def execute(self, actor: Profile, salon_id: str, reason: str, details: str) -> dict:
        if not actor.is_active or actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")
        await self.repository.get_public_salon(salon_id)
        return await self.repository.create_salon_report(actor.id, salon_id, reason, details)
