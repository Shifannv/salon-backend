"""Customer authorization and orchestration for database-owned booking changes."""

from datetime import date
from typing import Any

from app.application.ports.booking_changes import BookingChangeGateway
from app.core.exceptions import ForbiddenError, IdempotencyKeyRequiredError
from app.domain.entities.profile import Profile, Role


class BookingChangeUseCases:
    def __init__(self, repository: BookingChangeGateway):
        self.repository = repository

    @staticmethod
    def authorize(actor: Profile) -> None:
        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer booking access required")

    async def quote(self, actor: Profile, booking_id: str, values: dict[str, Any]) -> dict[str, Any]:
        self.authorize(actor)
        return await self.repository.quote(booking_id, values)

    async def availability(self, actor: Profile, booking_id: str, staff_id: str, services: list[str], day: date) -> list[dict[str, Any]]:
        self.authorize(actor)
        return await self.repository.availability(booking_id, staff_id, services, day)

    async def commit(self, actor: Profile, booking_id: str, values: dict[str, Any], key: str | None) -> dict[str, Any]:
        self.authorize(actor)
        if key is None or not 8 <= len(key) <= 128 or not key.strip():
            raise IdempotencyKeyRequiredError("Idempotency-Key must be 8-128 characters")
        return await self.repository.commit(booking_id, values, key)
