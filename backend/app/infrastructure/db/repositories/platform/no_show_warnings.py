"""No-show warnings: the salon warns a late customer, the customer replies, the clock auto-resolves."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.infrastructure.db.repositories.platform._sql import _booking_actor_sql

_log = logging.getLogger(__name__)

MAX_WARNINGS_PER_BOOKING = 2
AUTO_NO_SHOW_REASON = "Customer no-show: no reply to the arrival warning"


class NoShowWarningsMixin:
    """Warning rows live beside the booking; every change commits with its notifications."""

    session: AsyncSession

    async def create_no_show_warning(
        self, actor_id: str, booking_id: str, grace_minutes: int, idempotency_key: str | None
    ) -> dict[str, Any]:
        """Open a warning on a confirmed booking whose start time has passed."""

        scope = f"booking:{booking_id}:no_show_warning"
        replay = await self.begin_booking_operation(  # type: ignore[attr-defined]
            actor_id, scope, idempotency_key, {"grace_minutes": grace_minutes}
        )
        if replay is not None:
            return {**replay, "_idempotency_replay": True}
        result = await self.session.execute(
            text(
                f"""
                select id, status, customer_id, staff_id, salon_id, start_datetime, now() as database_now
                from bookings
                where id = :booking_id and ({_booking_actor_sql("bookings")})
                for update
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        booking = result.mappings().one_or_none()
        if booking is None:
            raise NotFoundError("Booking not found")
        if booking["status"] != "confirmed":
            raise ConflictError("Booking state changed; refresh before deciding")
        if booking["customer_id"] is None:
            raise ValidationError("This booking has no customer account to warn")
        if booking["database_now"] < booking["start_datetime"]:
            raise ValidationError("Wait until the appointment time before warning the customer")
        history = await self.session.execute(
            text(
                "select count(*) as total, count(*) filter (where resolved_at is null) as open "
                "from booking_no_show_warnings where booking_id = :booking_id"
            ),
            {"booking_id": booking_id},
        )
        counts = history.mappings().one()
        if counts["open"]:
            raise ConflictError("The customer has already been warned")
        if counts["total"] >= MAX_WARNINGS_PER_BOOKING:
            raise ConflictError("The customer has already been warned twice for this booking")
        inserted = await self.session.execute(
            text(
                """
                insert into booking_no_show_warnings (booking_id, salon_id, staff_id, warned_by, grace_minutes, deadline_at)
                values (:booking_id, :salon_id, :staff_id, :actor_id, :grace, now() + make_interval(mins => :grace))
                returning deadline_at
                """
            ),
            {
                "booking_id": booking_id, "salon_id": booking["salon_id"], "staff_id": booking["staff_id"],
                "actor_id": actor_id, "grace": grace_minutes,
            },
        )
        deadline_at = inserted.scalar_one()
        outbox_id = await self._insert_notification_outbox(  # type: ignore[attr-defined]
            user_id=str(booking["customer_id"]),
            booking_id=booking_id,
            notification_type="booking_no_show_warning",
            title="The salon is waiting for you",
            body=f"Your booking will be cancelled in {grace_minutes} minutes unless you reply.",
            data={"booking_id": booking_id, "deadline_at": deadline_at.isoformat(), "grace_minutes": grace_minutes},
        )
        return await self._finish_warning_change(actor_id, booking_id, scope, idempotency_key, [outbox_id])

    async def withdraw_no_show_warning(self, actor_id: str, booking_id: str) -> dict[str, Any]:
        """Close an open warning because the customer arrived or the salon changed its mind."""

        result = await self.session.execute(
            text(
                f"""
                select id, customer_id from bookings
                where id = :booking_id and ({_booking_actor_sql("bookings")})
                for update
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        booking = result.mappings().one_or_none()
        if booking is None:
            raise NotFoundError("Booking not found")
        closed = await self.session.execute(
            text(
                """
                update booking_no_show_warnings set resolved_at = now(), resolution = 'withdrawn'
                where booking_id = :booking_id and resolved_at is null
                returning id
                """
            ),
            {"booking_id": booking_id},
        )
        if closed.first() is None:
            raise NotFoundError("There is no open warning for this booking")
        outbox_ids = []
        if booking["customer_id"] is not None:
            outbox_ids.append(
                await self._insert_notification_outbox(  # type: ignore[attr-defined]
                    user_id=str(booking["customer_id"]),
                    booking_id=booking_id,
                    notification_type="booking_no_show_warning_withdrawn",
                    title="Your booking is still active",
                    body="The salon cancelled the arrival warning. Your booking is still on.",
                )
            )
        return await self._finish_warning_change(actor_id, booking_id, None, None, outbox_ids)

    async def respond_to_no_show_warning(
        self, customer_id: str, booking_id: str, response: str,
        cancellation_reason: str | None, reason_code: str | None, reason_text: str | None,
    ) -> dict[str, Any]:
        """Record the customer's reply; "not_coming" cancels the booking in the same transaction."""

        booking_row = await self.session.execute(
            text(
                """
                select b.id, b.status, b.customer_name, b.staff_id, s.owner_id
                from bookings b join salons s on s.id = b.salon_id
                where b.id = :booking_id and b.customer_id = :customer_id
                for update of b
                """
            ),
            {"booking_id": booking_id, "customer_id": customer_id},
        )
        booking = booking_row.mappings().one_or_none()
        if booking is None:
            raise NotFoundError("Booking not found")
        warning_row = await self.session.execute(
            text(
                """
                select id, customer_response, now() >= deadline_at as expired
                from booking_no_show_warnings where booking_id = :booking_id and resolved_at is null
                for update
                """
            ),
            {"booking_id": booking_id},
        )
        warning = warning_row.mappings().one_or_none()
        if warning is None or booking["status"] != "confirmed":
            raise ConflictError("There is no open warning for this booking")
        if warning["expired"]:
            raise ConflictError("The reply window has closed")

        outbox_ids: list[str] = []
        recipients = await self._booking_staff_recipients(booking_id)
        if response == "on_the_way":
            if warning["customer_response"] != "on_the_way":
                await self.session.execute(
                    text(
                        """
                        update booking_no_show_warnings
                        set customer_response = 'on_the_way', responded_at = now() where id = :id
                        """
                    ),
                    {"id": warning["id"]},
                )
                for user_id in recipients:
                    outbox_ids.append(await self._insert_notification_outbox(  # type: ignore[attr-defined]
                        user_id=user_id, booking_id=booking_id, notification_type="booking_customer_on_the_way",
                        title="Customer is on the way", body=f"{booking['customer_name']} says they are on the way.",
                    ))
        else:
            await self._cancel_for_no_show_reply(booking_id, customer_id, cancellation_reason)
            await self.session.execute(
                text(
                    """
                    update booking_no_show_warnings
                    set customer_response = 'not_coming', responded_at = now(),
                        response_reason_code = :code, response_reason_text = :text,
                        resolved_at = now(), resolution = 'customer_cancelled'
                    where id = :id
                    """
                ),
                {"id": warning["id"], "code": reason_code, "text": reason_text},
            )
            for user_id in recipients:
                outbox_ids.append(await self._insert_notification_outbox(  # type: ignore[attr-defined]
                    user_id=user_id, booking_id=booking_id, notification_type="booking_customer_not_coming",
                    title="Customer is not coming",
                    body=f"{booking['customer_name']} cancelled: {cancellation_reason or 'no reason given'}.",
                ))
        return await self._finish_warning_change(customer_id, booking_id, None, None, outbox_ids)

    async def expire_no_show_warnings(self, limit: int = 20) -> int:
        """Mark bookings no-show when a warning ran out unanswered. Safe to run from several workers."""

        due = await self.session.execute(
            text(
                """
                select w.id as warning_id, w.booking_id, s.owner_id
                from booking_no_show_warnings w join salons s on s.id = w.salon_id
                where w.resolved_at is null and w.customer_response is null and w.deadline_at <= now()
                order by w.deadline_at limit :limit
                """
            ),
            {"limit": limit},
        )
        rows = [dict(row) for row in due.mappings().all()]
        await self.session.rollback()
        processed = 0
        for row in rows:
            booking_id = str(row["booking_id"])
            try:
                booking = await self.update_booking_status(  # type: ignore[attr-defined]
                    str(row["owner_id"]), booking_id, "no_show", cancellation_reason=AUTO_NO_SHOW_REASON,
                    only_unanswered_warning=True,
                )
            except (ConflictError, NotFoundError, ValidationError):
                await self.session.rollback()
                await self._close_stale_warning(str(row["warning_id"]), booking_id)
                continue
            except Exception:
                # A database rule (for example a finance review hold) must not stop the other warnings.
                await self.session.rollback()
                _log.exception("Automatic no-show failed for booking %s", booking_id)
                continue
            await self._notify_staff_of_auto_no_show(booking_id, booking["customer_name"])
            processed += 1
        return processed

    async def _finish_warning_change(
        self, actor_id: str, booking_id: str, scope: str | None, key: str | None, outbox_ids: list[str]
    ) -> dict[str, Any]:
        booking = await self.get_booking(booking_id, actor_id)  # type: ignore[attr-defined]
        if booking is None:
            raise NotFoundError("Booking not found")
        booking["_outbox_ids"] = outbox_ids
        if scope is not None:
            await self.finish_booking_operation(actor_id, scope, key, booking)  # type: ignore[attr-defined]
        await self.session.commit()
        return booking

    async def _cancel_for_no_show_reply(self, booking_id: str, customer_id: str, reason: str | None) -> None:
        # The ordinary customer cancel refuses once a booking has started, which is when warnings exist.
        await self.session.execute(text("select set_config('app.booking_cancel_origin','customer',true)"))
        await self.session.execute(
            text("update bookings set status = 'cancelled', cancellation_reason = :reason where id = :booking_id"),
            {"booking_id": booking_id, "reason": reason},
        )
        await self.session.execute(
            text(
                """
                update booking_action_requests
                set status = 'resolved', decision = 'invalidated',
                    decision_reason = 'Booking cancelled by customer after arrival warning',
                    resolved_by = :customer_id, resolved_at = now()
                where booking_id = :booking_id and status = 'pending'
                """
            ),
            {"booking_id": booking_id, "customer_id": customer_id},
        )

    async def _booking_staff_recipients(self, booking_id: str) -> list[str]:
        result = await self.session.execute(
            text(
                """
                select distinct u.user_id from (
                  select s.owner_id as user_id from bookings b join salons s on s.id = b.salon_id where b.id = :booking_id
                  union
                  select st.profile_id from bookings b join staff st on st.id = b.staff_id
                  where b.id = :booking_id and st.is_active
                ) u where u.user_id is not null
                """
            ),
            {"booking_id": booking_id},
        )
        return [str(row[0]) for row in result.all()]

    async def _close_stale_warning(self, warning_id: str, booking_id: str) -> None:
        # Only once the booking has left "confirmed"; a customer reply that won the race keeps its warning open.
        await self.session.execute(
            text(
                "update booking_no_show_warnings set resolved_at = now(), resolution = 'withdrawn' "
                "where id = :id and resolved_at is null "
                "and not exists (select 1 from bookings b where b.id = :booking_id and b.status = 'confirmed')"
            ),
            {"id": warning_id, "booking_id": booking_id},
        )
        await self.session.commit()

    async def _notify_staff_of_auto_no_show(self, booking_id: str, customer_name: str) -> None:
        for user_id in await self._booking_staff_recipients(booking_id):
            await self.enqueue_notification(  # type: ignore[attr-defined]
                user_id=user_id, booking_id=booking_id, notification_type="booking_no_show_auto",
                title="Marked as no-show", body=f"{customer_name} did not reply in time. Your next customer can sit.",
            )

