"""Booking and availability use cases."""

import logging
from datetime import date, datetime
from typing import Any

from fastapi import BackgroundTasks

from app.application.use_cases.workspace import assert_approved_workspace
from app.core.config import settings
from app.core.exceptions import (
    BookingSourceNotAllowedError,
    ForbiddenError,
    NotFoundError,
    OnlinePaymentUnavailableError,
    ValidationError,
)
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import is_owner_or_staff
from app.domain.services.booking_policy import can_record_payment
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

_log = logging.getLogger(__name__)

_CUSTOMER_REASON_LABELS: dict[str, str] = {
    "schedule_conflict": "Schedule conflict",
    "found_better": "Found a better option",
    "personal_emergency": "Personal emergency",
    "booked_by_mistake": "Booked by mistake",
    "service_not_needed": "Service no longer needed",
    "other": "Other reason",
}
_BARBER_REASON_LABELS: dict[str, str] = {
    "barber_unavailable": "Barber unavailable",
    "salon_emergency": "Salon emergency",
    "overbooking": "Overbooking",
    "customer_no_show": "Customer no-show",
    "equipment_issue": "Equipment issue",
    "other": "Other reason",
}


def _reason_key(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").casefold().split())


def compose_cancellation_reason(
    label: str | None, reason_code: str | None, reason_text: str | None
) -> str | None:
    """Join label and free text, dropping text that only repeats the code or label."""

    text = (reason_text or "").strip()
    if not text:
        return label
    if label is None:
        return text
    if _reason_key(text) in {_reason_key(label), _reason_key(reason_code or "")}:
        return label
    return f"{label} — {text}"


def validate_visit_itinerary(values: dict[str, Any]) -> None:
    """Keep quote and creation tied to the same complete, duplicate-free itinerary."""

    segments = values.get("segments")
    if not segments:
        return
    flattened = [str(sid) for segment in segments for sid in segment["service_ids"]]
    if (len(flattened) != len(set(flattened)) or sorted(flattened) != sorted(map(str, values["service_ids"]))
        or str(segments[0]["staff_id"]) != str(values["staff_id"])):
        raise ValidationError("Selected services must match the complete itinerary")


class BookingUseCases:
    """Booking and availability use cases."""

    def __init__(self, repository: PlatformRepository, *, online_payments_enabled: bool = False) -> None:
        self.repository = repository
        self.online_payments_enabled = online_payments_enabled

    async def availability(
        self, staff_id: str, booking_date: date, service_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Return available slots from the database function."""

        return await self.repository.get_available_slots(staff_id, booking_date, service_ids)

    async def visit_availability(self, salon_id: str, booking_date: date, segments: list[dict]) -> list[dict]:
        return await self.repository.get_visit_slots(salon_id, booking_date, segments)

    async def create_booking(
        self,
        actor: Profile,
        values: dict[str, Any],
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Create booking through the database function.

        Price, duration and end time are computed by Postgres from the service ids; the request carries
        no price. ``qr_walkin`` is set only by the QR route after it validates the token, so it cannot be
        claimed here.
        """

        if values.get("source") == "qr_walkin":
            raise BookingSourceNotAllowedError("Walk-in QR bookings are created through the QR route")
        if values.get("source") == "manual_walkin":
            await assert_approved_workspace(self.repository, actor)
        if values.get("source") == "manual_walkin" and actor.role not in {Role.owner, Role.staff}:
            raise ForbiddenError("Manual walk-in bookings require salon workspace access")
        if values.get("source") == "manual_walkin":
            salon = await self.repository.get_workspace_salon(actor.id)
            if salon is None or str(salon["id"]) != str(values["salon_id"]):
                raise ForbiddenError("You can create walk-in bookings only for your own salon")
        if values.get("source") == "app" and actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer app bookings require customer or owner access")
        if values.get("payment_preference") in {"pay_full", "pay_advance"} and not self.online_payments_enabled:
            raise OnlinePaymentUnavailableError("Online payment coming soon.")
        if values.get("segments"):
            validate_visit_itinerary(values)
            if values.get("payment_preference") not in {None,"pay_at_salon"}:
                raise OnlinePaymentUnavailableError("Multi-professional visits support Pay at Salon")
        await self.repository.get_public_salon(str(values["salon_id"]))
        booking = await self.repository.create_booking({**values, "actor_id": actor.id})
        replayed = booking.pop("_idempotency_replay", False)
        if not replayed and background_tasks is not None and values.get("source") != "manual_walkin":
            background_tasks.add_task(self.notify_new_booking_owner, booking)
            background_tasks.add_task(self.notify_new_booking_customer, booking)
        return booking

    async def notify_new_booking_customer(self, booking: dict[str, Any]) -> None:
        """Acknowledge a new app booking to the customer who made it."""

        if booking.get("status") == "confirmed":
            title, body, kind = (
                "Booking Confirmed",
                "Your appointment has been confirmed.",
                "booking_confirmed",
            )
        else:
            title, body, kind = (
                "Booking Requested",
                "Your booking request was sent. We'll notify you once the salon responds.",
                "booking_requested",
            )
        await self._notify_customer(booking, title, body, kind)

    async def notify_new_booking_owner(self, booking: dict[str, Any]) -> None:
        """Notify a salon owner about an app or QR booking."""

        await self._notify_salon_owner(
            booking,
            "New Booking",
            f"{booking.get('customer_name', 'A customer')} created a booking.",
            "new_booking",
        )

    async def list_bookings(
        self,
        actor: Profile,
        *,
        booking_statuses: list[str] | None = None,
        include_archived: bool = False,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List role-scoped bookings."""

        if actor.role in {Role.owner, Role.staff}:
            await assert_approved_workspace(self.repository, actor)
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationError("date_from must be on or before date_to")
        return await self.repository.list_bookings(
            actor.id,
            actor.role.value,
            booking_statuses=booking_statuses,
            include_archived=include_archived,
            source=source,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

    async def get_booking(self, actor: Profile, booking_id: str) -> dict[str, Any]:
        """Return a role-scoped booking."""

        booking = await self.repository.get_booking(booking_id, actor.id)
        if booking is None:
            raise NotFoundError("Booking not found")
        if actor.role == Role.staff or (
            actor.role == Role.owner and booking.get("customer_id") != actor.id
        ):
            await assert_approved_workspace(self.repository, actor)
        return booking

    async def set_archived(self, actor: Profile, booking_id: str, archived: bool) -> dict[str, Any]:
        """Let the salon owner hide or restore a finished booking in the workspace list."""

        if actor.role != Role.owner:
            raise ForbiddenError("Salon owner access required")
        await assert_approved_workspace(self.repository, actor)
        return await self.repository.set_booking_archived(actor.id, booking_id, archived)

    async def approve(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Approve a booking and notify the customer."""

        await assert_approved_workspace(self.repository, actor)
        booking = await self.repository.update_booking_status(actor.id, booking_id, "confirmed")
        if background_tasks is not None:
            background_tasks.add_task(
                self._notify_customer, booking, "Booking Confirmed",
                "Your appointment has been confirmed.", "booking_confirmed"
            )
        return booking

    async def reject(
        self,
        actor: Profile,
        booking_id: str,
        rejection_reason: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Reject a booking and notify the customer."""

        await assert_approved_workspace(self.repository, actor)
        booking = await self.repository.update_booking_status(
            actor.id, booking_id, "rejected", rejection_reason=rejection_reason
        )
        if background_tasks is not None:
            background_tasks.add_task(
                self._notify_customer, booking, "Booking Rejected",
                f"Your appointment was declined: {rejection_reason}", "booking_rejected"
            )
        return booking

    async def complete(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
        *, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Complete a booking."""

        await assert_approved_workspace(self.repository, actor)
        kwargs = {"idempotency_key": idempotency_key} if idempotency_key else {}
        booking = await self.repository.update_booking_status(actor.id, booking_id, "completed", **kwargs)
        replayed = booking.pop("_idempotency_replay", False)
        if not replayed and background_tasks is not None:
            background_tasks.add_task(
                self._notify_customer, booking, "Visit Complete",
                "Thank you for your visit!", "booking_completed"
            )
        return booking

    async def mark_attendance(
        self, actor: Profile, booking_id: str, *, no_show: bool,
        idempotency_key: str | None, reason: str | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        await assert_approved_workspace(self.repository, actor)
        if no_show and (not isinstance(reason, str) or not reason.strip()):
            raise ValidationError("A reason is required when marking a customer as a no-show")
        values = {"cancellation_reason": reason.strip()} if no_show else {}
        booking = await self.repository.update_booking_status(
            actor.id, booking_id, "no_show" if no_show else "checked_in",
            idempotency_key=idempotency_key, **values,
        )
        self._schedule_booking_outbox(booking, background_tasks)
        return booking

    async def cancellation_quote(self, actor: Profile, booking_id: str) -> dict[str, Any]:
        from decimal import Decimal

        from app.domain.services.booking_finance_policy import POLICY_VERSION, cancellation_quote

        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer booking access required")
        booking = await self.repository.get_booking(booking_id, actor.id)
        if booking is None or str(booking.get("customer_id")) != actor.id:
            raise NotFoundError("Booking not found")
        funds = await self.repository.cancellation_payment_summary(actor.id, booking_id)
        captured, refunded = funds["captured"], funds["refunded"]
        refund = Decimal("0")
        deduction = Decimal("0")
        message = "No online payment was collected. There is no online refund to process."
        review = False
        if captured > 0:
            if booking.get("checkout_policy_version") == POLICY_VERSION:
                quote = cancellation_quote(captured, booking["start_datetime"], funds["database_now"], Decimal("0"))
                refund = max(Decimal("0"), min(captured-refunded, quote.customer_refund-refunded))
                deduction = quote.penalty
                message = "Refund eligibility is estimated now and recalculated when you confirm. Cancellation releases the slot; refund processing is separate."
            else:
                refund = None
                deduction = None
                review = True
                message = "This booking uses an earlier payment policy. Refund details require review; cancelling does not mean a refund has completed."
        elif booking.get("paid_amount", Decimal("0")) > 0:
            review = True
            refund = None
            deduction = None
            message = "Payment was recorded at the salon. Contact the salon about returning that payment; this app will not issue an online refund for it."
        return {"booking_id": booking_id,
            "can_cancel": booking["status"] in {"pending", "confirmed"} and funds["database_now"] < booking["start_datetime"],
            "payment_preference": booking.get("payment_preference"), "paid_online": captured>0,
            "currency": booking.get("currency", "INR"), "amount_paid": captured, "already_refunded": refunded,
            "refund_amount": refund, "deduction_amount": deduction, "message": message, "requires_review": review}

    async def cancel(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
        *,
        reason_code: str | None = None,
        reason_text: str | None = None,
    ) -> dict[str, Any]:
        """Cancel a visible booking and persist an optional audit-friendly reason."""

        label = _CUSTOMER_REASON_LABELS.get(
            reason_code,
            reason_code.replace("_", " ").capitalize() if reason_code else None,
        )
        cancellation_reason = compose_cancellation_reason(label, reason_code, reason_text)

        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer booking access required")
        booking = await self.repository.cancel_customer_booking(
            actor.id,
            booking_id,
            cancellation_reason,
            settings.customer_cancellation_cutoff_minutes,
        )
        self._schedule_booking_outbox(booking, background_tasks)
        return booking

    async def delay(
        self,
        actor: Profile,
        booking_id: str,
        estimated_end_datetime: datetime,
        notify_affected_customers: bool,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Record a delayed completion estimate and optionally notify later customers."""

        await assert_approved_workspace(self.repository, actor)
        current = await self.get_booking(actor, booking_id)
        if estimated_end_datetime <= current["end_datetime"]:
            raise ValidationError("estimated_end_datetime must be later than end_datetime")
        booking = await self.repository.delay_booking(
            actor.id, booking_id, estimated_end_datetime
        )
        if notify_affected_customers and background_tasks is not None:
            background_tasks.add_task(
                self._notify_delay_affected_customers,
                booking_id,
                estimated_end_datetime,
            )
        return booking

    async def barber_cancel(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
        *,
        reason_code: str,
        reason_text: str | None = None,
    ) -> dict[str, Any]:
        """Cancel a booking as the barber/owner — reason is required.

        Builds a human-readable ``cancellation_reason`` string from the
        structured ``reason_code`` and optional free-text ``reason_text``,
        persists it to ``bookings.cancellation_reason``, and notifies the
        customer via push so they see the reason immediately.

        Args:
            actor: Must be owner or staff of the booking's salon.
            booking_id: UUID of the booking to cancel.
            background_tasks: FastAPI background task runner for push delivery.
            reason_code: Structured code from ``BarberCancellationReasonCode``.
            reason_text: Optional free-text context appended to the reason.
        """

        await assert_approved_workspace(self.repository, actor)

        label = _BARBER_REASON_LABELS.get(reason_code, reason_code.replace("_", " ").capitalize())
        cancellation_reason = compose_cancellation_reason(label, reason_code, reason_text)

        booking = await self.repository.update_booking_status(
            actor.id,
            booking_id,
            "cancelled",
            cancellation_reason=cancellation_reason,
        )
        self._schedule_booking_outbox(booking, background_tasks)
        return booking

    async def record_payment(
        self,
        actor: Profile,
        booking_id: str,
        payment_method: str,
        background_tasks: BackgroundTasks | None = None,
        *, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Record booking payment."""

        await assert_approved_workspace(self.repository, actor)
        if not is_owner_or_staff(actor) or not can_record_payment(actor):
            raise ForbiddenError("Salon workspace access required")
        if payment_method not in {"cash", "upi_direct"}:
            raise ValidationError("Select Cash or direct UPI to mark payment collected")
        kwargs = {"idempotency_key": idempotency_key} if idempotency_key else {}
        booking = await self.repository.record_payment(
            actor.id, booking_id, payment_method, **kwargs
        )
        self._schedule_booking_outbox(booking, background_tasks)
        return booking

    def _schedule_booking_outbox(
        self,
        booking: dict[str, Any],
        background_tasks: BackgroundTasks | None,
    ) -> None:
        """Attempt notifications persisted with a booking transition."""

        if background_tasks is None:
            return
        from app.infrastructure.push.outbox_worker import (
            deliver_notification_outbox_event,
        )

        for outbox_id in booking.get("_outbox_ids", []):
            background_tasks.add_task(deliver_notification_outbox_event, outbox_id)

    async def _notify_customer(
        self,
        booking: dict[str, Any],
        title: str,
        body: str,
        notification_type: str,
    ) -> None:
        """Create and deliver a notification to the booking customer."""

        customer_id = booking.get("customer_id")
        if customer_id:
            await self._notify_user(
                str(customer_id), str(booking["id"]), notification_type, title, body
            )

    async def _notify_salon_owner(
        self,
        booking: dict[str, Any],
        title: str,
        body: str,
        notification_type: str,
    ) -> None:
        """Create and deliver a booking notification to the salon owner."""

        owner_id = booking.get("salon_owner_id")
        if owner_id:
            await self._notify_user(
                str(owner_id), str(booking["id"]), notification_type, title, body
            )

    async def _notify_delay_affected_customers(
        self, booking_id: str, estimated_end_datetime: datetime
    ) -> None:
        """Notify later customers whose appointments overlap the delay window."""

        affected = await self.repository.list_delay_affected_bookings(
            booking_id, estimated_end_datetime
        )
        for booking in affected:
            await self._notify_user(
                str(booking["customer_id"]),
                str(booking["id"]),
                "booking_delayed",
                "Appointment Delay",
                "Your appointment may start later than scheduled. Please check the latest details.",
            )

    async def _notify_user(
        self,
        user_id: str,
        booking_id: str,
        notification_type: str,
        title: str,
        body: str,
    ) -> None:
        """Persist and fan out one notification without failing the booking workflow."""

        try:
            from app.infrastructure.push.outbox_worker import (
                enqueue_and_deliver_notification,
            )

            await enqueue_and_deliver_notification(
                user_id=user_id,
                booking_id=booking_id,
                notification_type=notification_type,
                title=title,
                body=body,
            )
        except Exception as exc:
            _log.warning(
                "Failed to send notification for booking %s: %s",
                booking_id,
                type(exc).__name__,
            )
