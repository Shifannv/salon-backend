"""Admin-only finance decisions; no external transfer is initiated here."""

from decimal import Decimal
from typing import Any

from app.application.ports.booking_finance import BookingFinanceGateway
from app.application.use_cases.idempotency import check_idempotency_key_length
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Profile, Role


class BookingFinanceUseCases:
    def __init__(self, repository: BookingFinanceGateway) -> None:
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
        check_idempotency_key_length(key, max_len=128)
        await self.repository.command(booking_id, version, key, action, amount, reference)
        return await self.repository.statement(booking_id, actor.id, admin=True)
