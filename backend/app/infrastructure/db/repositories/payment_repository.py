"""Raw-SQL repository for the payment ledger, refunds, webhook intake and idempotency.

Kept apart from ``platform_repository.py`` on purpose. Amounts are only ever read here
(``bookings.total_price`` / ``deposit_amount`` were computed in SQL); nothing recomputes
a price. Booking-level payment columns are written solely by the database's
``recompute_booking_payment_state`` trigger path.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.payments._sql import _OPEN, _SETTLED
from app.infrastructure.db.repositories.payments.earnings import EarningsMixin
from app.infrastructure.db.repositories.payments.idempotency import IdempotencyMixin
from app.infrastructure.db.repositories.payments.intents import IntentMixin
from app.infrastructure.db.repositories.payments.observations import ObservationMixin
from app.infrastructure.db.repositories.payments.provider_accounts import ProviderAccountMixin
from app.infrastructure.db.repositories.payments.refunds import RefundMixin
from app.infrastructure.db.repositories.payments.webhook_events import WebhookEventMixin
from app.infrastructure.db.session import set_actor_context

__all__ = ["_OPEN", "_SETTLED", "PaymentRepository"]


class PaymentRepository(
    IdempotencyMixin,
    IntentMixin,
    RefundMixin,
    ObservationMixin,
    WebhookEventMixin,
    ProviderAccountMixin,
    EarningsMixin,
):
    """Database adapter for payments."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def set_actor(self, actor_id: str) -> None:
        """Re-arm the audit actor: ``set_config(..., true)`` dies with each commit."""

        await set_actor_context(self.session, actor_id)
