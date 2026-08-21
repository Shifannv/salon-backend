"""Frontend-facing platform use cases."""

import logging
import uuid
from datetime import date
from typing import Any

from fastapi import BackgroundTasks

from app.application.ports.storage_gateway import _UPLOAD_TTL_SECONDS, StorageGateway
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import is_owner_or_staff
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

_log = logging.getLogger(__name__)


def _derive_extension(filename: str) -> str:
    """Derive a safe file extension from the client-supplied filename.

    Falls back to 'jpeg' when the extension is absent or unrecognised.
    """
    if "." in filename:
        raw_ext = filename.rsplit(".", 1)[-1].lower()
        if raw_ext in {"jpg", "jpeg", "png", "webp", "heic", "heif"}:
            return "jpeg" if raw_ext == "jpg" else raw_ext
    return "jpeg"


def _extract_r2_object_key(public_url: str, r2_public_base: str) -> str | None:
    """Extract the R2 object key from a public URL.

    Returns the path component after the R2 public base URL, or ``None`` if
    the URL does not belong to this R2 bucket (e.g. an external avatar URL).

    Args:
        public_url: The full public URL stored in the database.
        r2_public_base: The configured R2_PUBLIC_URL base (e.g. 'https://pub-xxx.r2.dev').

    Returns:
        Object key string (e.g. 'avatars/abc/avatar.jpeg'), or None.
    """
    base = r2_public_base.rstrip("/")
    if public_url.startswith(base + "/"):
        return public_url[len(base) + 1:]
    return None


def _upload_result(upload_url: str, public_url: str) -> dict[str, Any]:
    """Return the standard upload URL response payload."""
    return {
        "upload_url": upload_url,
        "public_url": public_url,
        "expires_in": _UPLOAD_TTL_SECONDS,
    }


class CustomerUseCases:
    """Customer app use cases."""

    def __init__(
        self,
        repository: PlatformRepository,
        storage_gateway: StorageGateway | None = None,
    ) -> None:
        self.repository = repository
        self.storage_gateway = storage_gateway

    async def update_profile(
        self,
        actor: Profile,
        values: dict[str, Any],
        *,
        bucket: str | None = None,
        r2_public_base: str | None = None,
    ) -> dict[str, Any]:
        """Update the customer profile owned by the actor.

        When ``avatar_url`` is being replaced and both ``bucket`` and
        ``r2_public_base`` are provided (and a storage gateway is wired in),
        the previous R2 object is deleted best-effort before returning.  The
        deletion never raises — a warning is logged on failure so the profile
        update is never blocked.

        Args:
            actor: Authenticated profile (customer or owner).
            values: Fields to update (``exclude_unset`` dict from Pydantic).
            bucket: R2 bucket name; required to trigger old-avatar cleanup.
            r2_public_base: Configured R2_PUBLIC_URL; used to extract the
                object key from the stored public URL.
        """

        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")

        # --- Best-effort cleanup of the previous avatar from R2 ---
        new_avatar_url = values.get("avatar_url")
        old_avatar_url = actor.avatar_url
        should_cleanup = (
            new_avatar_url is not None           # caller is changing the avatar
            and new_avatar_url != old_avatar_url  # it is actually a different URL
            and old_avatar_url                    # there is an existing avatar to remove
            and self.storage_gateway is not None
            and bucket is not None
            and r2_public_base is not None
        )
        if should_cleanup:
            old_key = _extract_r2_object_key(str(old_avatar_url), str(r2_public_base))
            if old_key:
                try:
                    await self.storage_gateway.delete_object(bucket, old_key)  # type: ignore[union-attr]
                except Exception:
                    _log.warning(
                        "Failed to delete old avatar from R2 (key=%s). "
                        "Profile update will still proceed.",
                        old_key,
                    )

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
        ids: list[str] | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """List customer-visible salons.

        Services are NOT included. Use GET /salons/{salon_id}/services for service data.
        Pass ``category`` (e.g. ``"Hair Cutting"``) to filter salons by service category;
        the backend does a case-insensitive ILIKE match against ``service_categories.name``.
        """

        return await self.repository.list_salons(
            search=search,
            city=city,
            lat=lat,
            lng=lng,
            limit=limit,
            offset=offset,
            ids=ids,
            category=category,
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

    async def get_avatar_upload_url(
        self,
        actor: Profile,
        content_type: str,
        filename: str,
        bucket: str,
    ) -> dict[str, Any]:
        """Generate a presigned R2 upload URL for a user profile avatar.

        Available to all authenticated roles (customer, owner, staff).
        The client should:
        1. Receive ``upload_url`` and ``public_url`` from this method.
        2. PUT the image binary directly to ``upload_url`` with the matching Content-Type header.
        3. Call PATCH /profiles/me with { "avatar_url": public_url } to record the URL.

        Args:
            actor: Authenticated profile (any role).
            content_type: MIME type of the image.
            filename: Original filename; used only to derive the file extension.
            bucket: R2 bucket name (read from settings in the router).

        Returns:
            Dict with keys: upload_url, public_url, expires_in.
        """
        if not self.storage_gateway:
            raise ValidationError(
                "Image upload is not configured on this server (R2 storage gateway is missing)."
            )

        ext = _derive_extension(filename)
        # Use a fixed canonical key so re-uploads overwrite the previous object
        # in R2 rather than accumulating orphaned blobs.
        object_key = f"avatars/{actor.id}/avatar.{ext}"

        upload_url = await self.storage_gateway.get_upload_url(bucket, object_key, content_type)
        public_url = self.storage_gateway.get_public_url(bucket, object_key)
        return _upload_result(upload_url, public_url)


class OwnerUseCases:
    """Barber/owner app use cases."""

    def __init__(
        self,
        repository: PlatformRepository,
        storage_gateway: StorageGateway | None = None,
    ) -> None:
        self.repository = repository
        self.storage_gateway = storage_gateway

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

    async def complete_profile(self, actor: Profile, values: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create/update the actor's salon profile and mark it complete."""

        self._assert_owner_workspace(actor)
        return await self.repository.complete_owner_salon(actor.id, values or {})

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
        """Not yet implemented — salon images have no is_active column for soft delete.

        Raises ``ValidationError`` so the HTTP layer returns 501 Not Implemented.
        The route exists as a stub so the API surface is complete when the migration lands.
        """

        raise ValidationError("Image deletion is not yet implemented. The schema does not support soft delete for salon images.")

    async def get_image_upload_url(
        self,
        actor: Profile,
        content_type: str,
        filename: str,
        bucket: str,
    ) -> dict[str, Any]:
        """Generate a presigned R2 upload URL for a salon gallery image.

        The client should:
        1. Receive ``upload_url`` and ``public_url`` from this method.
        2. PUT the image binary directly to ``upload_url`` with the matching Content-Type header.
        3. Call POST /owner/me/images with { "url": public_url } to record the image in the DB.

        Args:
            actor: Authenticated owner/staff profile.
            content_type: MIME type of the image (e.g. 'image/jpeg', 'image/png').
            filename: Original filename; used only to derive the file extension.
            bucket: R2 bucket name (read from settings in the router).

        Returns:
            Dict with keys: upload_url, public_url, expires_in.
        """
        self._assert_owner_workspace(actor)

        if not self.storage_gateway:
            raise ValidationError(
                "Image upload is not configured on this server (R2 storage gateway is missing)."
            )

        salon = await self.get_my_salon(actor)
        salon_id = str(salon["id"])

        ext = _derive_extension(filename)
        object_key = f"salon-images/{salon_id}/{uuid.uuid4()}.{ext}"

        upload_url = await self.storage_gateway.get_upload_url(bucket, object_key, content_type)
        public_url = self.storage_gateway.get_public_url(bucket, object_key)
        return _upload_result(upload_url, public_url)

    async def get_staff_photo_upload_url(
        self,
        actor: Profile,
        staff_id: str,
        content_type: str,
        filename: str,
        bucket: str,
    ) -> dict[str, Any]:
        """Generate a presigned R2 upload URL for a staff member's photo.

        The client should:
        1. Receive ``upload_url`` and ``public_url`` from this method.
        2. PUT the image binary directly to ``upload_url`` with the matching Content-Type header.
        3. Call PATCH /owner/me/staff/{staff_id} with { "photo_url": public_url } to record it.

        Args:
            actor: Authenticated owner/staff profile.
            staff_id: ID of the staff member whose photo is being uploaded.
            content_type: MIME type of the image.
            filename: Original filename; used only to derive the file extension.
            bucket: R2 bucket name (read from settings in the router).

        Returns:
            Dict with keys: upload_url, public_url, expires_in.
        """
        self._assert_owner_workspace(actor)

        if not self.storage_gateway:
            raise ValidationError(
                "Image upload is not configured on this server (R2 storage gateway is missing)."
            )

        salon = await self.get_my_salon(actor)
        salon_id = str(salon["id"])

        ext = _derive_extension(filename)
        # Use a fixed canonical key so re-uploads overwrite the previous object
        # in R2 rather than accumulating orphaned blobs.
        object_key = f"staff-photos/{salon_id}/{staff_id}/photo.{ext}"

        upload_url = await self.storage_gateway.get_upload_url(bucket, object_key, content_type)
        public_url = self.storage_gateway.get_public_url(bucket, object_key)
        return _upload_result(upload_url, public_url)

    async def list_holidays(self, actor: Profile) -> list[dict[str, Any]]:
        """List salon holidays."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_holidays(actor.id)

    async def create_holiday(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create a salon holiday."""

        self._assert_owner_workspace(actor)
        return await self.repository.create_holiday(actor.id, values)

    async def delete_holiday(self, _actor: Profile, _holiday_id: str) -> None:
        """Not yet implemented — holidays have no deletion route in the schema.

        Raises ``ValidationError`` so the HTTP layer returns 501 Not Implemented.
        The route exists as a stub so the API surface is complete when supported.
        """

        raise ValidationError("Holiday deletion is not yet implemented.")

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

    async def list_staff_services(
        self, actor: Profile, staff_id: str
    ) -> list[dict[str, Any]]:
        """List service assignments for staff."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_staff_services(actor.id, staff_id)

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
        if values.get("source") == "app" and actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer app bookings require customer or owner access")
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
