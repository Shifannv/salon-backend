"""Frontend-facing platform use cases."""

import logging
from datetime import date
from typing import Any

from fastapi import BackgroundTasks

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import is_customer, is_owner_or_staff
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

_log = logging.getLogger(__name__)


class CustomerUseCases:
    """Customer app use cases."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    async def update_profile(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Update the customer profile owned by the actor."""

        if not is_customer(actor):
            raise ForbiddenError("Customer access required")
        return await self.repository.update_profile(actor.id, values)

    async def list_salons(
        self,
        *,
        search: str | None,
        city: str | None,
        lat: float | None,
        lng: float | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """List customer-visible salons."""

        return await self.repository.list_salons(
            search=search, city=city, lat=lat, lng=lng, limit=limit, offset=offset
        )

    async def get_salon(self, salon_id: str) -> dict[str, Any]:
        """Return customer-visible salon details."""

        return await self.repository.get_public_salon(salon_id)

    async def list_salon_services(self, salon_id: str) -> list[dict[str, Any]]:
        """Return customer-visible services for a salon."""

        return await self.repository.list_public_services(salon_id)

    async def list_salon_staff(self, salon_id: str) -> list[dict[str, Any]]:
        """Return active staff for a customer-visible salon."""

        return await self.repository.list_public_staff(salon_id)


class OwnerUseCases:
    """Barber/owner app use cases."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def _assert_owner_workspace(self, actor: Profile) -> None:
        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")

    async def get_my_salon(self, actor: Profile) -> dict[str, Any]:
        """Return the actor's salon."""

        self._assert_owner_workspace(actor)
        return await self.repository.get_owner_salon(actor.id)

    async def update_my_salon(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Update the actor's salon."""

        self._assert_owner_workspace(actor)
        return await self.repository.update_owner_salon(actor.id, values)

    async def complete_profile(self, actor: Profile) -> dict[str, Any]:
        """Mark the actor's salon profile as complete."""

        self._assert_owner_workspace(actor)
        return await self.repository.complete_owner_salon(actor.id)

    async def list_images(self, actor: Profile) -> list[dict[str, Any]]:
        """List salon images."""

        salon = await self.get_my_salon(actor)
        return await self.repository.list_salon_images(str(salon["id"]))

    async def create_image(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create a salon image."""

        self._assert_owner_workspace(actor)
        return await self.repository.create_salon_image(actor.id, values)

    async def update_image(
        self, actor: Profile, image_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a salon image."""

        self._assert_owner_workspace(actor)
        return await self.repository.update_salon_image(actor.id, image_id, values)

    async def delete_image(self, _actor: Profile, _image_id: str) -> None:
        """Reject image deletion until the schema supports soft delete."""

        raise ValidationError("Salon images do not support soft delete in the current schema")

    async def list_holidays(self, actor: Profile) -> list[dict[str, Any]]:
        """List salon holidays."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_holidays(actor.id)

    async def create_holiday(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create a salon holiday."""

        self._assert_owner_workspace(actor)
        return await self.repository.create_holiday(actor.id, values)

    async def delete_holiday(self, _actor: Profile, _holiday_id: str) -> None:
        """Reject holiday deletion until the schema supports soft delete."""

        raise ValidationError("Salon holidays do not support soft delete in the current schema")

    async def list_services(self, actor: Profile) -> list[dict[str, Any]]:
        """List owner services."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_owner_services(actor.id)

    async def create_service(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create owner service."""

        self._assert_owner_workspace(actor)
        return await self.repository.create_owner_service(actor.id, values)

    async def update_service(
        self, actor: Profile, service_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update owner service."""

        self._assert_owner_workspace(actor)
        return await self.repository.update_owner_service(actor.id, service_id, values)

    async def deactivate_service(self, actor: Profile, service_id: str) -> dict[str, Any]:
        """Soft-delete owner service."""

        self._assert_owner_workspace(actor)
        return await self.repository.deactivate_owner_service(actor.id, service_id)

    async def list_staff(self, actor: Profile) -> list[dict[str, Any]]:
        """List owner staff."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_owner_staff(actor.id)

    async def create_staff(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create owner staff."""

        self._assert_owner_workspace(actor)
        return await self.repository.create_owner_staff(actor.id, values)

    async def update_staff(
        self, actor: Profile, staff_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update owner staff."""

        self._assert_owner_workspace(actor)
        return await self.repository.update_owner_staff(actor.id, staff_id, values)

    async def deactivate_staff(self, actor: Profile, staff_id: str) -> dict[str, Any]:
        """Soft-delete owner staff."""

        self._assert_owner_workspace(actor)
        return await self.repository.deactivate_owner_staff(actor.id, staff_id)

    async def assign_staff_service(
        self, actor: Profile, staff_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Assign service to staff."""

        self._assert_owner_workspace(actor)
        return await self.repository.assign_staff_service(actor.id, staff_id, values)

    # --- Staff service language assignments ---

    async def list_staff_service_languages(
        self, actor: Profile, staff_id: str, staff_service_id: str
    ) -> list[dict[str, Any]]:
        """List languages for a staff service assignment."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_staff_service_languages(
            actor.id, staff_id, staff_service_id
        )

    async def set_staff_service_languages(
        self,
        actor: Profile,
        staff_id: str,
        staff_service_id: str,
        language_codes: list[str],
    ) -> list[dict[str, Any]]:
        """Replace the language list for a staff service (idempotent PUT)."""

        self._assert_owner_workspace(actor)
        return await self.repository.set_staff_service_languages(
            actor.id, staff_id, staff_service_id, language_codes
        )

    # --- Blocked slots ---

    async def list_blocked_slots(self, actor: Profile) -> list[dict[str, Any]]:
        """List blocked slots for the owner's salon."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_blocked_slots(actor.id)

    async def create_blocked_slot(
        self, actor: Profile, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a staff-scoped or salon-wide blocked slot."""

        self._assert_owner_workspace(actor)
        return await self.repository.create_blocked_slot(actor.id, values)

    async def delete_blocked_slot(self, actor: Profile, slot_id: str) -> None:
        """Delete a blocked slot.

        Blocked slots have no is_active column in the schema, so this is a
        hard delete — the schema intentionally treats them as ephemeral entries.
        """

        self._assert_owner_workspace(actor)
        await self.repository.delete_blocked_slot(actor.id, slot_id)


class BookingUseCases:
    """Booking and availability use cases."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    async def availability(
        self, staff_id: str, booking_date: date, service_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Return available slots from the database function."""

        return await self.repository.get_available_slots(staff_id, booking_date, service_ids)

    async def create_booking(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create booking through the database function."""

        if values.get("source") == "manual_walkin" and actor.role not in {Role.owner, Role.staff}:
            raise ForbiddenError("Manual walk-in bookings require salon workspace access")
        if values.get("source") == "app" and actor.role != Role.customer:
            raise ForbiddenError("Customer app bookings require customer access")
        return await self.repository.create_booking({**values, "actor_id": actor.id})

    async def list_bookings(self, actor: Profile) -> list[dict[str, Any]]:
        """List role-scoped bookings."""

        return await self.repository.list_bookings(actor.id, actor.role.value)

    async def get_booking(self, actor: Profile, booking_id: str) -> dict[str, Any]:
        """Return a role-scoped booking."""

        booking = await self.repository.get_booking(booking_id, actor.id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def approve(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Approve a booking and notify the customer."""

        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
        booking = await self.repository.update_booking_status(actor.id, booking_id, "confirmed")
        if background_tasks is not None:
            background_tasks.add_task(
                self._notify_customer, booking, "Booking Confirmed",
                "Your appointment has been confirmed."
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

        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
        booking = await self.repository.update_booking_status(
            actor.id, booking_id, "rejected", rejection_reason=rejection_reason
        )
        if background_tasks is not None:
            background_tasks.add_task(
                self._notify_customer, booking, "Booking Rejected",
                f"Your appointment was declined: {rejection_reason}"
            )
        return booking

    async def complete(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Complete a booking."""

        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
        booking = await self.repository.update_booking_status(actor.id, booking_id, "completed")
        if background_tasks is not None:
            background_tasks.add_task(
                self._notify_customer, booking, "Visit Complete",
                "Thank you for your visit!"
            )
        return booking

    async def cancel(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
        *,
        reason_code: str | None = None,
        reason_text: str | None = None,
    ) -> dict[str, Any]:
        """Cancel a booking with role-scoped ownership.

        ``reason_code`` mirrors the frontend ``CancellationReasonChip`` values;
        ``reason_text`` holds any free-text note. Both are accepted so the
        endpoint returns 200 instead of 422 when the frontend sends a body,
        but they are **not** persisted to the ``bookings`` row (no column
        exists for them in the current schema). The frontend stores the full
        ``CancellationRecord`` directly to Supabase's ``cancellation_records``
        table in a separate call.
        """

        booking = await self.repository.update_booking_status(
            actor.id,
            booking_id,
            "cancelled",
            customer_only=actor.role == Role.customer,
        )
        if background_tasks is not None and actor.role != Role.customer:
            # Notify the customer when the salon cancels
            background_tasks.add_task(
                self._notify_customer, booking, "Booking Cancelled",
                "Your appointment has been cancelled by the salon."
            )
        return booking

    async def record_payment(
        self, actor: Profile, booking_id: str, payment_method: str
    ) -> dict[str, Any]:
        """Record booking payment."""

        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
        return await self.repository.record_payment(actor.id, booking_id, payment_method)

    async def _notify_customer(
        self, booking: dict[str, Any], title: str, body: str
    ) -> None:
        """Create a notification row and fan-out push to the customer's devices.

        Runs as a background task so it never blocks the HTTP response.
        The FCMGateway is a no-op if Firebase is not configured.
        """

        customer_id = booking.get("customer_id")
        if not customer_id:
            # Manual walk-in with no account — no one to notify.
            return

        try:
            notification = await self.repository.create_notification(
                user_id=str(customer_id),
                booking_id=str(booking["id"]),
                notification_type="booking_status",
                title=title,
                body=body,
            )
            # Lazy import: firebase-admin is optional — only needed when FCM is configured.
            from app.core.config import settings
            from app.infrastructure.push.fcm_gateway import FCMGateway

            fcm = FCMGateway(settings, self.repository.session)
            await fcm.fan_out(str(notification["id"]), str(customer_id))
        except Exception:
            # Push delivery failures must never affect the booking workflow.
            _log.warning(
                "Failed to send push notification for booking %s", booking.get("id")
            )


class NotificationUseCases:
    """Notification and device use cases."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    async def list_notifications(self, actor: Profile) -> list[dict[str, Any]]:
        """List actor notifications."""

        return await self.repository.list_notifications(actor.id)

    async def mark_read(self, actor: Profile, notification_id: str) -> dict[str, Any]:
        """Mark notification as read."""

        return await self.repository.mark_notification_read(actor.id, notification_id)

    async def register_device(
        self,
        actor: Profile,
        token: str,
        platform: str | None,
        device_name: str | None,
    ) -> dict[str, Any]:
        """Register actor device token (idempotent — reactivates if it already exists)."""

        return await self.repository.register_device(actor.id, token, platform, device_name)

    async def deactivate_device(self, actor: Profile, token: str) -> None:
        """Deactivate this specific device token for the actor."""

        await self.repository.deactivate_device_for_actor(actor.id, token)
