"""Booking status changes, cancellation and delay."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BookingChangeError,
    ConflictError,
    NotFoundError,
    PaymentCollectionRequiredError,
    ValidationError,
)
from app.domain.services.booking_finance_policy import POLICY_VERSION, validate_no_show
from app.infrastructure.db.repositories.platform._sql import _booking_actor_sql
from app.infrastructure.db.repositories.staff_earnings_repository import record_staff_earnings

_ARCHIVABLE_STATUSES = frozenset({"cancelled", "rejected", "no_show", "completed"})


class BookingUpdatesMixin:
    """Booking status changes, cancellation and delay."""

    session: AsyncSession

    async def set_booking_archived(self, actor_id: str, booking_id: str, archived: bool) -> dict[str, Any]:
        """Let the salon owner hide or show a finished booking; status and money are never touched."""

        result = await self.session.execute(
            text(
                """
                select status, owner_archived_at is not null as is_archived from bookings
                where id = :booking_id
                  and exists (select 1 from salons s where s.id = bookings.salon_id and s.owner_id = :actor_id)
                for update
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        current = result.mappings().one_or_none()
        if current is None:
            raise NotFoundError("Booking not found")
        if current["status"] not in _ARCHIVABLE_STATUSES:
            raise ConflictError("Only finished bookings can be archived")
        if current["is_archived"] != archived:
            await self.session.execute(
                text(
                    "update bookings set owner_archived_at = case when cast(:archived as boolean) then now() else null end "
                    "where id = :booking_id"
                ),
                {"archived": archived, "booking_id": booking_id},
            )
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        # Commit only after the re-read succeeds so a failed read never leaves a half-applied change.
        await self.session.commit()
        return booking

    async def update_booking_status(
        self,
        actor_id: str,
        booking_id: str,
        status: str,
        *,
        rejection_reason: str | None = None,
        cancellation_reason: str | None = None,
        customer_only: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Apply an authorized, valid booking transition under a row lock."""
        scope = f"booking:{booking_id}:{status}"
        replay = await self.begin_booking_operation(actor_id, scope, idempotency_key, {
            "status": status, "rejection_reason": rejection_reason, "cancellation_reason": cancellation_reason,
        })
        if replay is not None:
            return {**replay, "_idempotency_replay": True}

        owner_predicate = _booking_actor_sql("bookings")
        predicate = "customer_id = :actor_id" if customer_only else owner_predicate
        current_result = await self.session.execute(
            text(
                f"""
                select id, status, customer_id, customer_name, payment_status, payment_preference, checkout_policy_version,
                       start_datetime, now() as database_now,
                       (select w.deadline_at from booking_no_show_warnings w
                         where w.booking_id = bookings.id and w.resolved_at is null) as warning_deadline
                from bookings
                where id = :booking_id and ({predicate})
                for update
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        current = current_result.mappings().one_or_none()
        if current is None:
            raise NotFoundError("Booking not found")
        allowed = {
            "pending": {"confirmed", "rejected", "cancelled"},
            "confirmed": {"checked_in", "completed", "cancelled", "no_show"},
            "checked_in": {"completed", "cancelled", "no_show"},
        }
        if status not in allowed.get(current["status"], set()):
            raise ConflictError("Booking state changed; refresh before deciding")
        no_show = status == "no_show" or (
            status == "cancelled" and (cancellation_reason or "").startswith("Customer no-show")
        )
        if no_show:
            if current["status"] == "checked_in":
                raise ConflictError("A checked-in customer cannot be marked as a no-show")
            try:
                cancellation_reason = validate_no_show(
                    current["start_datetime"], current["database_now"], cancellation_reason,
                    current.get("warning_deadline"),
                )
            except ValueError as error:
                message = (
                    "Wait until 10 minutes after the appointment starts before marking a no-show"
                    if error.args == ("no_show_grace_period",)
                    else "A reason is required when marking a customer as a no-show"
                )
                raise ValidationError(message) from None
        if status == "completed" and (current.get("payment_preference") == "pay_at_salon"
                or current.get("checkout_policy_version") == POLICY_VERSION) and current.get("payment_status") != "paid":
            raise PaymentCollectionRequiredError("Collect cash or direct UPI from customer before completing service.")
        if status == "cancelled":
            if current.get("checkout_policy_version") == POLICY_VERSION and current["status"] == "checked_in":
                raise BookingChangeError("cancellation_review_required", "Cancellation after check-in requires finance review")
            await self.session.execute(text("select set_config('app.booking_cancel_origin',:origin,true)"),
                                       {"origin": "customer" if customer_only else "salon"})

        await self.session.execute(
            text(
                """
                update bookings
                set status = cast(:status as booking_status),
                    rejection_reason = coalesce(:rejection_reason, rejection_reason),
                    cancellation_reason = coalesce(:cancellation_reason, cancellation_reason)
                where id = :booking_id
                """
            ),
            {
                "actor_id": actor_id,
                "booking_id": booking_id,
                "status": status,
                "rejection_reason": rejection_reason,
                "cancellation_reason": cancellation_reason,
            },
        )
        if status in {"checked_in", "rejected", "cancelled", "completed", "no_show"}:
            resolution = (
                "arrived" if status == "checked_in" else "no_show" if status == "no_show"
                else "customer_cancelled" if status == "cancelled" and customer_only else "withdrawn"
            )
            await self.session.execute(
                text(
                    "update booking_no_show_warnings set resolved_at = now(), resolution = :resolution "
                    "where booking_id = :booking_id and resolved_at is null"
                ),
                {"booking_id": booking_id, "resolution": resolution},
            )
        if status == "completed":
            # What each service earned its staff member, written in this same transaction (S1a).
            await record_staff_earnings(self.session, booking_id)
        if status in {"rejected", "cancelled", "completed", "no_show"}:
            invalidated_kinds = (
                ["cancellation"]
                if status == "completed"
                else ["cancellation", "payment_confirmation"]
            )
            await self.session.execute(
                text(
                    """
                    update booking_action_requests
                    set status = 'resolved',
                        decision = 'invalidated',
                        decision_reason = :reason,
                        resolved_by = :actor_id,
                        resolved_at = now()
                    where booking_id = :booking_id
                      and status = 'pending'
                      and kind in (
                        select value
                        from jsonb_array_elements_text(cast(:kinds_json as jsonb)) value
                      )
                    """
                ),
                {
                    "actor_id": actor_id,
                    "booking_id": booking_id,
                    "kinds_json": json.dumps(invalidated_kinds),
                    "reason": f"Booking changed to {status}",
                },
            )
        outbox_ids: list[str] = []
        if no_show and current["customer_id"]:
            outbox_ids.append(
                await self._insert_notification_outbox(
                    user_id=str(current["customer_id"]),
                    booking_id=booking_id,
                    notification_type="booking_no_show",
                    title="Appointment marked as no-show",
                    body=f"The salon marked that you did not attend: {cancellation_reason}",
                )
            )
        elif status == "cancelled" and current["customer_id"]:
            outbox_ids.append(
                await self._insert_notification_outbox(
                    user_id=str(current["customer_id"]),
                    booking_id=booking_id,
                    notification_type="booking_cancelled",
                    title="Booking cancelled by salon",
                    body=(
                        "The salon cancelled your appointment: "
                        f"{cancellation_reason or 'Please contact the salon for details.'}"
                    ),
                    audience="customer",
                )
            )
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        booking["_outbox_ids"] = outbox_ids
        await self.finish_booking_operation(actor_id, scope, idempotency_key, booking)
        await self.session.commit()
        return booking

    async def cancellation_payment_summary(self, actor_id: str, booking_id: str) -> dict[str, Any]:
        result = await self.session.execute(text("""
          SELECT statement_timestamp() database_now,
            coalesce((SELECT sum(amount-overcollected_amount) FROM public.booking_payments
              WHERE booking_id=b.id AND channel='gateway' AND status IN ('captured','partially_refunded','refunded')),0) captured,
            coalesce((SELECT sum(r.amount) FROM public.payment_refunds r JOIN public.booking_payments p ON p.id=r.payment_id
              WHERE r.booking_id=b.id AND p.channel='gateway' AND r.status='processed' AND NOT r.applies_to_excess),0) refunded
          FROM public.bookings b WHERE b.id=:id AND b.customer_id=:actor
        """), {"id": booking_id, "actor": actor_id})
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Booking not found")
        return dict(row)

    async def cancel_customer_booking(
        self,
        actor_id: str,
        booking_id: str,
        cancellation_reason: str | None,
        cutoff_minutes: int,
    ) -> dict[str, Any]:
        """Cancel an owned booking before its start, using the database wall clock."""

        result = await self.session.execute(
            text(
                """
                with locked as materialized (
                    select b.id, b.status, b.start_datetime, b.customer_name, b.checkout_policy_version,
                           s.owner_id
                    from bookings b
                    join salons s on s.id = b.salon_id
                    where b.id = :booking_id and b.customer_id = :actor_id
                    for update of b
                ) select locked.*, clock_timestamp() as database_now from locked
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Booking not found")
        if row["status"] not in {"pending", "confirmed"}:
            raise ConflictError("Booking can no longer be cancelled")
        if row["database_now"] >= row["start_datetime"]:
            raise ConflictError("This appointment has started. Contact the salon for help.")

        # Trusted provenance also distinguishes an owner cancelling a self-booked visit.
        await self.session.execute(text("select set_config('app.booking_cancel_origin','customer',true)"))

        await self.session.execute(
            text(
                """
                update bookings
                set status = 'cancelled', cancellation_reason = :cancellation_reason
                where id = :booking_id
                """
            ),
            {
                "booking_id": booking_id,
                "cancellation_reason": cancellation_reason,
            },
        )
        await self.session.execute(
            text(
                """
                update booking_action_requests
                set status = 'resolved', decision = 'invalidated',
                    decision_reason = 'Booking cancelled directly by customer',
                    resolved_by = :actor_id, resolved_at = now()
                where booking_id = :booking_id and status = 'pending'
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        outbox_id = await self._insert_notification_outbox(
            user_id=str(row["owner_id"]),
            booking_id=booking_id,
            notification_type="booking_cancelled",
            title="Booking cancelled",
            body=f"{row['customer_name']} cancelled their appointment.",
            audience="owner",
        )
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        booking["_outbox_ids"] = [outbox_id]
        await self.session.commit()
        return booking

    async def delay_booking(
        self,
        actor_id: str,
        booking_id: str,
        estimated_end_datetime: datetime,
    ) -> dict[str, Any]:
        """Set an estimated completion time for an owner/staff-visible booking."""

        result = await self.session.execute(
            text(
                f"""
                update bookings
                set estimated_end_datetime = :estimated_end_datetime
                where id = :booking_id
                  and status in ('pending', 'confirmed')
                  and {_booking_actor_sql("bookings")}
                returning id
                """
            ),
            {
                "actor_id": actor_id,
                "booking_id": booking_id,
                "estimated_end_datetime": estimated_end_datetime,
            },
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError("Active booking not found")
        await self.session.commit()
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def list_delay_affected_bookings(
        self, booking_id: str, estimated_end_datetime: datetime
    ) -> list[dict[str, Any]]:
        """Return later customer bookings that overlap a delayed completion estimate."""

        result = await self.session.execute(
            text(
                """
                select affected.id, affected.customer_id, affected.start_datetime
                from bookings current_booking
                join bookings affected
                  on affected.staff_id = current_booking.staff_id
                 and affected.id <> current_booking.id
                 and affected.status in ('pending', 'confirmed')
                 and affected.start_datetime >= current_booking.end_datetime
                 and affected.start_datetime < :estimated_end_datetime
                where current_booking.id = :booking_id
                  and affected.customer_id is not null
                order by affected.start_datetime
                """
            ),
            {
                "booking_id": booking_id,
                "estimated_end_datetime": estimated_end_datetime,
            },
        )
        return [dict(row) for row in result.mappings().all()]
