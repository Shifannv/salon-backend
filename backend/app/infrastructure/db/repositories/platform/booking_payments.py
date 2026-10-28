"""Manual payment receipts."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PaymentInProgressError,
)
from app.infrastructure.db.repositories.platform._sql import (
    _RECORD_PAYMENT_ERROR_RULES,
    _booking_actor_sql,
    _error_for_message,
)


class BookingPaymentsMixin:
    """Manual payment receipts."""

    session: AsyncSession

    async def _insert_manual_payment(
        self, *, booking_id: str, actor_id: str, method: str
    ) -> None:
        """Write the manual receipt as a ledger row; the trigger settles payment_status.

        The caller must hold the booking row lock. The amount is whatever the ledger says is
        still outstanding, so recording the balance after an online deposit settles exactly
        the remainder (and can never over-collect: the database raises
        ``payment_overcollection`` otherwise).
        """

        gateway_open = await self.session.execute(
            text(
                """
                select 1 from booking_payments
                where booking_id = :booking_id and channel = 'gateway'
                  and status in ('created', 'authorized')
                limit 1
                """
            ),
            {"booking_id": booking_id},
        )
        if gateway_open.first() is not None:
            raise PaymentInProgressError(
                "An online payment is in progress for this booking; wait for it to settle "
                "or ask the customer to cancel it"
            )
        try:
            await self.session.execute(
                text(
                    """
                    insert into booking_payments
                      (booking_id, salon_id, payer_id, recorded_by, channel, purpose,
                       settlement_model, method, amount, currency, status, intent_reference,
                       captured_at, collection_method, collected_by_owner)
                    select b.id, b.salon_id, b.customer_id, :actor_id, 'manual',
                           case when b.paid_amount - b.refunded_amount > 0
                                then 'balance' else 'full' end,
                           'offline', case when cast(:method as text) = 'cash' then 'cash' else 'online' end,
                           greatest(b.total_price - (b.paid_amount - b.refunded_amount), 0),
                           b.currency, 'captured', 'manual:' || gen_random_uuid()::text, now(),
                           case when cast(:method as text) = 'cash' then 'CASH' else 'UPI_DIRECT' end,
                           exists(select 1 from salons s where s.id=b.salon_id and s.owner_id=:actor_id)
                    from bookings b
                    where b.id = :booking_id
                    """
                ),
                {"booking_id": booking_id, "actor_id": actor_id, "method": method},
            )
        except DBAPIError as exc:
            await self.session.rollback()
            mapped = _error_for_message(str(exc), _RECORD_PAYMENT_ERROR_RULES)
            if mapped is not None:
                raise mapped from exc
            raise

    async def record_payment(
        self, actor_id: str, booking_id: str, payment_method: str, *, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        """Record an eligible owner-side payment exactly once."""
        scope = f"booking:{booking_id}:collect"
        replay = await self.begin_booking_operation(actor_id, scope, idempotency_key, {"method": payment_method})
        if replay is not None:
            return replay

        result = await self.session.execute(
            text(
                f"""
                select b.id, b.status, b.payment_status, b.customer_id
                from bookings b
                where b.id = :booking_id
                  and {_booking_actor_sql("b")}
                for update of b
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Booking not found")
        if row["status"] not in {"confirmed", "checked_in", "completed"}:
                raise ConflictError("Only confirmed, checked-in or completed bookings can be paid")
        if row["payment_status"] == "paid":
            raise ConflictError("Payment has already been recorded")

        await self._insert_manual_payment(
            booking_id=booking_id,
            actor_id=actor_id,
            method=payment_method,
        )
        await self.session.execute(
            text(
                """
                update booking_action_requests
                set status = 'resolved', decision = 'received',
                    decision_reason = 'Payment recorded directly by salon',
                    resolved_by = :actor_id, resolved_at = now()
                where booking_id = :booking_id
                  and kind = 'payment_confirmation'
                  and status = 'pending'
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        outbox_ids: list[str] = []
        if row["customer_id"]:
            outbox_ids.append(
                await self._insert_notification_outbox(
                    user_id=str(row["customer_id"]),
                    booking_id=booking_id,
                    notification_type="payment_received",
                    title="Payment received",
                    body="The salon recorded your payment and receipt.",
                )
            )
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        booking["_outbox_ids"] = outbox_ids
        await self.finish_booking_operation(actor_id, scope, idempotency_key, booking)
        await self.session.commit()
        return booking
