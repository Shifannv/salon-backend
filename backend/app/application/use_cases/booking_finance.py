"""Admin-only finance decisions; no external transfer is initiated here."""

from decimal import Decimal
from typing import Any

from app.application.ports.booking_finance import BookingFinanceGateway
from app.core.exceptions import ForbiddenError, IdempotencyKeyRequiredError
from app.domain.entities.profile import Profile, Role


class BookingFinanceUseCases:
    def __init__(self, repository: BookingFinanceGateway):
        self.repository = repository

    async def statement(self, actor: Profile, booking_id: str, *, admin: bool = False) -> dict[str, Any]:
        if admin and actor.role != Role.super_admin:
            raise ForbiddenError("Finance administrator access required")
        if not admin and actor.role != Role.owner:
            raise ForbiddenError("Salon owner access required")
        return await self.repository.statement(booking_id, actor.id, admin=admin)

    async def command(self, actor: Profile, booking_id: str, version: int, key: str | None,
                      action: str, amount: Decimal, reference: str) -> dict[str, Any]:
        if actor.role != Role.super_admin:
            raise ForbiddenError("Finance administrator access required")
        if key is None or not 8 <= len(key) <= 128 or not key.strip():
            raise IdempotencyKeyRequiredError("Idempotency-Key must be 8-128 characters")
        await self.repository.command(booking_id, version, key, action, amount, reference)
        return await self.repository.statement(booking_id, actor.id, admin=True)
