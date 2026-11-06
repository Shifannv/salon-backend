"""Customer authorization and orchestration for database-owned booking changes."""

from datetime import date
from typing import Any

from app.application.ports.booking_changes import BookingChangeGateway
from app.application.use_cases.idempotency import check_idempotency_key_length
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Profile, Role


class BookingChangeUseCases:
    def __init__(self, repository: BookingChangeGateway) -> None:
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

    async def visit_availability(self, actor: Profile, booking_id: str, segments: list[dict[str, Any]], day: date) -> list[dict[str, Any]]:
        self.authorize(actor)
        return await self.repository.visit_availability(booking_id, segments, day)

    async def commit(self, actor: Profile, booking_id: str, values: dict[str, Any], key: str | None) -> dict[str, Any]:
        self.authorize(actor)
        check_idempotency_key_length(key, max_len=128)
        return await self.repository.commit(booking_id, values, key)
