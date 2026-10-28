"""Booking action requests."""

from datetime import timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BookingChangeError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.domain.services.booking_finance_policy import POLICY_VERSION
from app.infrastructure.db.repositories.platform._sql import _salon_actor_sql, page_bounds


class BookingActionRequestsMixin:
    """Booking action requests."""

    session: AsyncSession

    async def _get_booking_action_request_row(
        self, request_id: str
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                select
                  ar.id, ar.booking_id, ar.kind, ar.status, ar.reason,
                  ar.decision, ar.decision_reason, ar.resolved_at, ar.created_at,
                  b.customer_name, b.start_datetime, b.total_price,
                  coalesce(
                    array(
                      select bs.service_name
                      from booking_services bs
                      where bs.booking_id = b.id and coalesce((to_jsonb(bs)->>'is_active')::boolean, true)
                      order by bs.service_name
                    ), array[]::text[]
                  ) as service_names
                from booking_action_requests ar
                join bookings b on b.id = ar.booking_id
                where ar.id = :request_id
                """
            ),
            {"request_id": request_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        item = dict(row)
        item["id"] = str(item["id"])
        item["booking_id"] = str(item["booking_id"])
        return item

    async def create_booking_action_request(
        self,
        actor_id: str,
        booking_id: str,
        kind: str,
        reason: str | None,
        *,
        cancellation_cutoff_minutes: int,
        allow_late_cancellation_requests: bool,
    ) -> dict[str, Any]:
        """Create an eligible customer request under a booking row lock."""

        result = await self.session.execute(
            text(
                """
                select b.id, b.status, b.payment_status, b.payment_preference, b.checkout_policy_version,
                       b.start_datetime, b.end_datetime, b.customer_name,
                       s.owner_id, now() as database_now
                from bookings b
                join salons s on s.id = b.salon_id
                where b.id = :booking_id and b.customer_id = :actor_id
                for update of b
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        booking = result.mappings().one_or_none()
        if booking is None:
            raise NotFoundError("Booking not found")

        if kind == "cancellation" and booking.get("checkout_policy_version") == POLICY_VERSION:
            raise BookingChangeError("direct_cancellation_required", "Cancel this booking directly to apply its stored cancellation policy")

        if kind == "payment_confirmation":
            if booking["status"] not in {"confirmed", "completed"}:
                raise ConflictError(
                    "Payment confirmation is allowed only for confirmed or completed bookings"
                )
            if booking["payment_status"] != "unpaid":
                raise ConflictError("Payment has already been recorded")
            if booking["payment_preference"] != "pay_at_salon":
                raise ConflictError("Booking is not configured for Pay at Salon")
            if booking["database_now"] < booking["start_datetime"]:
                raise ConflictError(
                    "Payment can be confirmed only after the salon visit starts"
                )
            title = "Customer reports payment"
            body = f"{booking['customer_name']} says they paid at the salon."
            notification_type = "payment_confirmation_requested"
        elif kind == "cancellation":
            if not allow_late_cancellation_requests:
                raise ConflictError("Late cancellation requests are disabled")
            if booking["status"] not in {"pending", "confirmed"}:
                raise ConflictError("Booking can no longer be cancelled")
            if booking["database_now"] >= booking["end_datetime"]:
                raise ConflictError("The appointment has already ended")
            cutoff = booking["start_datetime"] - timedelta(
                minutes=cancellation_cutoff_minutes
            )
            if booking["database_now"] < cutoff:
                raise ConflictError(
                    "Use immediate cancellation before the cancellation cutoff"
                )
            title = "Cancellation approval requested"
            body = f"{booking['customer_name']} requested a late cancellation."
            notification_type = "cancellation_requested"
        else:
            raise ValidationError("Unsupported booking action request kind")

        pending = await self.session.execute(
            text(
                """
                select id from booking_action_requests
                where booking_id = :booking_id and kind = :kind and status = 'pending'
                """
            ),
            {"booking_id": booking_id, "kind": kind},
        )
        if pending.scalar_one_or_none() is not None:
            raise ConflictError("A pending request already exists for this booking")

        created = await self.session.execute(
            text(
                """
                insert into booking_action_requests (
                  booking_id, kind, reason, requested_by, created_by, updated_by
                ) values (
                  :booking_id, :kind, :reason, :actor_id, :actor_id, :actor_id
                )
                returning id
                """
            ),
            {
                "booking_id": booking_id,
                "kind": kind,
                "reason": (reason or "").strip() or None,
                "actor_id": actor_id,
            },
        )
        request_id = str(created.scalar_one())
        outbox_id = await self._insert_notification_outbox(
            user_id=str(booking["owner_id"]),
            booking_id=booking_id,
            notification_type=notification_type,
            title=title,
            body=body,
        )
        item = await self._get_booking_action_request_row(request_id)
        if item is None:
            raise NotFoundError("Booking action request not found")
        item["_outbox_ids"] = [outbox_id]
        await self.session.commit()
        return item

    async def list_booking_action_requests(
        self,
        actor_id: str,
        request_status: str | None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List action requests visible to an owner or salon staff member."""

        result = await self.session.execute(
            text(
                f"""
                select
                  ar.id, ar.booking_id, ar.kind, ar.status, ar.reason,
                  ar.decision, ar.decision_reason, ar.resolved_at, ar.created_at,
                  b.customer_name, b.start_datetime, b.total_price,
                  coalesce(
                    array(
                      select bs.service_name from booking_services bs
                      where bs.booking_id = b.id and coalesce((to_jsonb(bs)->>'is_active')::boolean, true) order by bs.service_name
                    ), array[]::text[]
                  ) as service_names
                from booking_action_requests ar
                join bookings b on b.id = ar.booking_id
                join salons s on s.id = b.salon_id
                where (cast(:request_status as text) is null
                       or ar.status::text = cast(:request_status as text))
                  and {_salon_actor_sql("b")}
                order by ar.created_at, ar.id
                limit :limit offset :offset
                """
            ),
            {"actor_id": actor_id, "request_status": request_status, **page_bounds(limit, offset)},
        )
        items = []
        for row in result.mappings().all():
            item = dict(row)
            item["id"] = str(item["id"])
            item["booking_id"] = str(item["booking_id"])
            items.append(item)
        return items

    async def respond_booking_action_request(
        self,
        actor_id: str,
        request_id: str,
        decision: str,
        reason: str | None,
        payment_method: str = "cash",
    ) -> dict[str, Any]:
        """Resolve one request and transition its booking atomically."""

        result = await self.session.execute(
            text(
                f"""
                select ar.id, ar.kind, ar.status as request_status, ar.reason,
                       b.id as booking_id, b.status as booking_status,
                       b.payment_status, b.customer_id, b.end_datetime,
                       now() as database_now
                from booking_action_requests ar
                join bookings b on b.id = ar.booking_id
                join salons s on s.id = b.salon_id
                where ar.id = :request_id
                  and {_salon_actor_sql("b")}
                for update of b
                """
            ),
            {"actor_id": actor_id, "request_id": request_id},
        )
        current = result.mappings().one_or_none()
        if current is None:
            raise NotFoundError("Booking action request not found")
        if current["request_status"] != "pending":
            raise ConflictError("This request has already been resolved")
        request_lock = await self.session.execute(
            text(
                """
                select status from booking_action_requests
                where id = :request_id
                for update
                """
            ),
            {"request_id": request_id},
        )
        locked_request = request_lock.mappings().one_or_none()
        if locked_request is None or locked_request["status"] != "pending":
            raise ConflictError("This request has already been resolved")

        normalized_reason = (reason or "").strip() or None
        if current["kind"] == "payment_confirmation":
            if decision not in {"received", "not_received"}:
                raise ValidationError("Payment requests accept received or not_received")
            if current["booking_status"] not in {"confirmed", "completed"}:
                raise ConflictError("Booking is no longer eligible for payment")
            if current["payment_status"] != "unpaid":
                raise ConflictError("Payment has already been recorded")
            if decision == "received":
                # The method is the salon's statement of how the customer actually paid;
                # it used to be hardcoded to 'cash'.
                await self._insert_manual_payment(
                    booking_id=str(current["booking_id"]),
                    actor_id=actor_id,
                    method=payment_method,
                )
                title = "Payment received"
                body = (
                    "The salon confirmed your cash payment. Your receipt is recorded."
                    if payment_method == "cash"
                    else "The salon confirmed your payment. Your receipt is recorded."
                )
                notification_type = "payment_received"
            else:
                title = "Payment not received"
                body = normalized_reason or (
                    "The salon could not confirm your payment. You can try again after checking with them."
                )
                notification_type = "payment_not_received"
        else:
            if decision not in {"approve", "decline"}:
                raise ValidationError("Cancellation requests accept approve or decline")
            if current["booking_status"] not in {"pending", "confirmed"}:
                raise ConflictError("Booking is no longer eligible for cancellation")
            if current["database_now"] >= current["end_datetime"]:
                raise ConflictError("The appointment has already ended")
            if decision == "decline" and normalized_reason is None:
                raise ValidationError("A reason is required when declining cancellation")
            if decision == "approve":
                cancellation_reason = current["reason"] or (
                    "Late cancellation approved by salon"
                )
                await self.session.execute(
                    text(
                        """
                        update bookings
                        set status = 'cancelled', cancellation_reason = :reason
                        where id = :booking_id
                          and status in ('pending', 'confirmed')
                        """
                    ),
                    {
                        "booking_id": current["booking_id"],
                        "reason": cancellation_reason,
                    },
                )
                await self.session.execute(
                    text(
                        """
                        update booking_action_requests
                        set status = 'resolved', decision = 'invalidated',
                            decision_reason = 'Booking cancellation was approved',
                            resolved_by = :actor_id, resolved_at = now()
                        where booking_id = :booking_id
                          and id <> :request_id
                          and status = 'pending'
                        """
                    ),
                    {
                        "actor_id": actor_id,
                        "booking_id": current["booking_id"],
                        "request_id": request_id,
                    },
                )
                title = "Cancellation approved"
                body = "The salon approved your cancellation and released the appointment."
                notification_type = "cancellation_approved"
            else:
                title = "Cancellation declined"
                body = normalized_reason
                notification_type = "cancellation_declined"

        # Persist the decision message that the customer receives, even when
        # the owner did not provide an optional explanation.
        decision_reason = normalized_reason or body
        await self.session.execute(
            text(
                """
                update booking_action_requests
                set status = 'resolved', decision = :decision,
                    decision_reason = :reason, resolved_by = :actor_id,
                    resolved_at = now()
                where id = :request_id and status = 'pending'
                """
            ),
            {
                "request_id": request_id,
                "decision": decision,
                "reason": decision_reason,
                "actor_id": actor_id,
            },
        )
        outbox_id = await self._insert_notification_outbox(
            user_id=str(current["customer_id"]),
            booking_id=str(current["booking_id"]),
            notification_type=notification_type,
            title=title,
            body=body,
        )
        item = await self._get_booking_action_request_row(request_id)
        if item is None:
            raise NotFoundError("Booking action request not found")
        booking = await self.get_booking(str(current["booking_id"]), actor_id)
        item["booking"] = booking
        item["_outbox_ids"] = [outbox_id]
        await self.session.commit()
        return item
