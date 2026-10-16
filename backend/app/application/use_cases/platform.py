"""Frontend-facing platform use cases."""

import logging
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import BackgroundTasks

from app.application.ports.image_processor import ImagePolicy
from app.application.ports.storage_gateway import _UPLOAD_TTL_SECONDS, StorageGateway
from app.application.use_cases.media_publication import validate_media_reference
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import is_owner, is_owner_or_staff
from app.domain.services.booking_policy import can_record_payment
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

_log = logging.getLogger(__name__)


def _upload_extension(filename: str, content_type: str) -> str:
    allowed = {"image/jpeg": {"jpg", "jpeg"}, "image/png": {"png"}, "image/webp": {"webp"}}
    extension = filename.rsplit(".", 1)[-1].lower()
    if content_type not in allowed or extension not in allowed[content_type]:
        raise ValidationError("Image filename and content type must agree; use JPEG, PNG or WebP")
    return "jpeg" if extension == "jpg" else extension


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

        New hosted avatars require owned processing proof. Previous managed objects
        are retired by the worker after committed reference checks. Legacy URLs
        may remain unchanged and are never swept.

        Args:
            actor: Authenticated profile (customer or owner).
            values: Fields to update (``exclude_unset`` dict from Pydantic).
            bucket: Retained for call compatibility; cleanup uses worker settings.
            r2_public_base: Retained for call compatibility.
        """

        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")

        avatar = values.get("avatar_url")
        bundled = {f"__char__char-{index}" for index in range(1, 16)} | {"avatar:curly", "avatar:beard", "avatar:geek"}
        if avatar and avatar not in bundled:
            # The auth snapshot can be stale after a concurrent replacement.
            # Lock first and compare with the current committed reference.
            await self.repository.lock_media_url(avatar)
            current = await self.repository.get_profile(actor.id)
            if current is None:
                raise NotFoundError("Profile not found")
            if avatar != current.get("avatar_url"):
                await validate_media_reference(self.repository, self.storage_gateway, avatar, f"avatars/{actor.id}/")
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
        surface: str | None = None,
        shuffle_seed: str = "default",
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
            surface=surface,
            shuffle_seed=shuffle_seed,
        )

    async def assert_public_salon(self, salon_id: str) -> None:
        """Require current database visibility before returning cached public data."""
        await self.repository.assert_public_salon(salon_id)

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
        """Generate a signed backend upload URL for a user profile avatar.

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

        Note:
            ``storage_gateway`` is always a fully configured ``R2StorageGateway``
            when called from the router — ``get_storage_gateway()`` validates R2
            env vars at dependency-injection time before this method is reached.
        """
        assert self.storage_gateway is not None, "storage_gateway is required for avatar upload"

        if not actor.is_active:
            raise ForbiddenError("Active account required")
        ext = _upload_extension(filename, content_type)
        # Use a new key so a failed/replayed upload cannot replace a published photo.
        object_key = f"avatars/{actor.id}/{uuid.uuid4().hex}.{ext}"

        upload_url = await self.storage_gateway.get_upload_url(bucket, object_key, content_type)
        public_url = self.storage_gateway.get_public_url(bucket, object_key)
        return _upload_result(upload_url, public_url)


PAYOUT_FIELDS = ("account_holder_name", "upi_id", "bank_name", "bank_account_number", "ifsc")


def validate_payout_account(merged: dict[str, Any]) -> None:
    """Validate the merged payout row. Messages never contain submitted values."""

    if not merged.get("account_holder_name"):
        raise ValidationError("Account holder name is required")
    if merged.get("ifsc") and not merged.get("bank_account_number"):
        raise ValidationError("An IFSC code needs a bank account number")
    if merged.get("bank_name") and not merged.get("bank_account_number"):
        raise ValidationError("A bank name needs a bank account number")
    if merged.get("bank_account_number") and not merged.get("ifsc"):
        raise ValidationError("A bank account number needs an IFSC code")
    has_bank = bool(merged.get("bank_account_number")) and bool(merged.get("ifsc"))
    if not merged.get("upi_id") and not has_bank:
        raise ValidationError("Add a UPI ID, or both a bank account number and IFSC code")


def mask_payout_account(row: dict[str, Any] | None) -> dict[str, Any]:
    """Build the public response; only the last 4 digits of the account survive."""

    if row is None:
        return {
            "configured": False, "account_holder_name": None, "upi_id": None,
            "bank_name": None, "bank_account_last4": None, "ifsc": None,
            "has_upi": False, "has_bank": False, "updated_at": None,
        }
    # The repository already masks inside Postgres; ``bank_account_number`` is accepted
    # only so a caller holding a full row can never leak more than four digits.
    last4 = row.get("bank_account_last4")
    if last4 is None and row.get("bank_account_number"):
        last4 = row["bank_account_number"][-4:]
    return {
        "configured": True,
        "account_holder_name": row["account_holder_name"],
        "upi_id": row.get("upi_id"),
        "bank_name": row.get("bank_name"),
        "bank_account_last4": last4,
        "ifsc": row.get("ifsc"),
        "has_upi": bool(row.get("upi_id")),
        "has_bank": bool(last4) and bool(row.get("ifsc")),
        "updated_at": row.get("updated_at"),
    }


def _has_open_day(hours: Any) -> bool:
    if not isinstance(hours, dict):
        return False
    return any(isinstance(day, dict) and day.get("open") for day in hours.values())


def build_setup_status(facts: dict[str, Any]) -> dict[str, Any]:
    """Turn raw salon facts into the ordered setup checklist."""

    def present(key: str) -> bool:
        value = facts.get(key)
        return isinstance(value, str) and bool(value.strip())

    items = [
        ("profile_basics", "Business details",
         "Add your salon name, category, address and city.",
         all(present(k) for k in ("name", "category", "address", "city")), "business_profile"),
        ("working_hours", "Working hours",
         "Choose the days and times you are open.",
         _has_open_day(facts.get("working_hours")), "working_hours"),
        ("photos", "Salon photos",
         "Add at least one photo of your salon.", bool(facts.get("has_photos")), "photos"),
        ("services", "Services",
         "Add at least one service customers can book.",
         bool(facts.get("has_services")), "services"),
        ("staff", "Staff",
         "Add at least one team member.", bool(facts.get("has_staff")), "staff"),
        ("payout", "Payout details",
         "Tell us where to send your customer payments.",
         bool(facts.get("has_payout")), "payout"),
    ]
    result = [
        {"key": key, "title": title, "description": desc, "done": done, "action": action}
        for key, title, desc, done, action in items
    ]
    completed = sum(1 for item in result if item["done"])
    return {
        "completed_count": completed,
        "total_count": len(result),
        "is_complete": completed == len(result),
        "items": result,
    }


class OwnerUseCases:
    """Barber/owner app use cases."""

    def __init__(
        self,
        repository: PlatformRepository,
        storage_gateway: StorageGateway | None = None,
        service_media_base: str | None = None,
    ) -> None:
        self.repository = repository
        self.storage_gateway = storage_gateway
        self.service_media_base = service_media_base

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

    async def update_settings(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Update owner settings; pausing bookings needs the approved salon's owner.

        ``accepting_bookings`` only gates *new* bookings (enforced in Postgres). It never
        cancels, moves or notifies about existing bookings.
        """

        if "accepting_bookings" in values:
            if not is_owner(actor):
                raise ForbiddenError("Only the salon owner can change booking availability")
            await assert_approved_workspace(self.repository, actor)
        return await self.update_my_salon(actor, values)

    async def get_business_salon(self, actor: Profile) -> dict[str, Any]:
        """Return the approved salon for operational tools such as walk-in QR."""
        await assert_approved_workspace(self.repository, actor)
        salon = await self.repository.get_workspace_salon(actor.id)
        if salon is None:
            raise NotFoundError("Salon workspace not found")
        return salon

    async def complete_profile(self, actor: Profile, values: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create/update the actor's salon profile and mark it complete."""

        self._assert_owner_workspace(actor)
        return await self.repository.complete_owner_salon(actor.id, values or {})

    # ── Payout account & setup checklist (owner only, not approval-gated) ──────
    # Like complete_profile/get_my_salon these deliberately skip
    # assert_approved_workspace: a brand-new owner must be able to finish setup
    # while the salon still awaits admin approval. Staff are NOT allowed.

    def _assert_owner_only(self, actor: Profile) -> None:
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can manage payout details")

    async def get_payout_account(self, actor: Profile) -> dict[str, Any]:
        """Return the masked payout account (never the full account number)."""

        self._assert_owner_only(actor)
        return mask_payout_account(await self.repository.get_payout_account(actor.id))

    async def update_payout_account(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Merge ``values`` into the stored payout account and return the masked result."""

        self._assert_owner_only(actor)

        row = await self.repository.update_payout_account(
            actor.id,
            {k: v for k, v in values.items() if k in PAYOUT_FIELDS},
            validate_payout_account,
        )
        return mask_payout_account(row)

    async def get_payout_history(self, actor: Profile, limit: int = 50) -> list[dict[str, Any]]:
        """Return who changed the payout destination and when (last four digits only)."""

        self._assert_owner_only(actor)
        return await self.repository.list_payout_account_history(actor.id, limit)

    async def get_setup_status(self, actor: Profile) -> dict[str, Any]:
        """Return the authoritative new-owner setup checklist."""

        self._assert_owner_only(actor)
        return build_setup_status(await self.repository.get_setup_facts(actor.id))

    async def list_images(self, actor: Profile) -> list[dict[str, Any]]:
        """List salon images."""

        salon = await self.get_my_salon(actor)
        return await self.repository.list_salon_images(str(salon["id"]))

    async def create_image(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create a salon image."""

        self._assert_owner_workspace(actor)
        await self._validate_salon_media(actor, values.get("url"))
        return await self.repository.create_salon_image(actor.id, values)

    async def update_image(
        self, actor: Profile, image_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a salon image."""

        self._assert_owner_workspace(actor)
        if values.get("url"):
            await self.repository.lock_media_url(values["url"])
            images = await self.list_images(actor)
            current = next((image for image in images if str(image["id"]) == image_id), None)
            if current is None:
                raise NotFoundError("Image not found")
            if values["url"] != current["url"]:
                await self._validate_salon_media(actor, values["url"])
        return await self.repository.update_salon_image(actor.id, image_id, values)

    async def _validate_salon_media(self, actor: Profile, url: str | None, policy: ImagePolicy | None = None) -> None:
        if url is not None:
            salon = await self.get_my_salon(actor)
            await validate_media_reference(self.repository, self.storage_gateway, url, f"salon-images/{salon['id']}/", policy)

    async def delete_image(
        self,
        actor: Profile,
        image_id: str,
        bucket: str,
        r2_public_base: str,
    ) -> None:
        """Soft-delete a salon image; defer binary retirement to the worker.

        Steps:
        1. Soft-delete the DB row (set is_active = false) and retrieve its URL.
        2. The worker checks other references before removing managed objects.
        3. Failed cleanup is retried by subsequent sweeps.

        Args:
            actor: Authenticated owner/staff profile.
            image_id: UUID of the image to delete.
            bucket: R2 bucket name (read from settings in the router).
            r2_public_base: Configured R2_PUBLIC_URL base used to derive the key.

        Raises:
            NotFoundError: If the image does not exist or belongs to another salon.
        """
        self._assert_owner_workspace(actor)

        deleted_url = await self.repository.delete_salon_image(actor.id, image_id)
        if deleted_url is None:
            raise NotFoundError("Image not found or already deleted")

        # The scheduled worker checks all references before retiring the object.

    async def get_image_upload_url(
        self,
        actor: Profile,
        content_type: str,
        filename: str,
        bucket: str,
    ) -> dict[str, Any]:
        """Generate a signed backend upload URL for a salon gallery image.

        The client should:
        1. Receive ``upload_url`` and ``public_url`` from this method.
        2. PUT the image binary directly to ``upload_url`` with the matching Content-Type header.
        3. Call POST /v1/salons/me/images with { "url": public_url } to record the image in the DB.

        Args:
            actor: Authenticated owner/staff profile.
            content_type: MIME type of the image (e.g. 'image/jpeg', 'image/png').
            filename: Original filename; used only to derive the file extension.
            bucket: R2 bucket name (read from settings in the router).

        Returns:
            Dict with keys: upload_url, public_url, expires_in.

        Note:
            ``storage_gateway`` is always a fully configured ``R2StorageGateway``
            when called from the router — ``get_storage_gateway()`` validates R2
            env vars at dependency-injection time before this method is reached.
        """
        self._assert_owner_workspace(actor)
        assert self.storage_gateway is not None, "storage_gateway is required for image upload"

        salon = await self.get_my_salon(actor)
        salon_id = str(salon["id"])

        ext = _upload_extension(filename, content_type)
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
        """Generate a signed backend upload URL for a staff member's photo.

        The client should:
        1. Receive ``upload_url`` and ``public_url`` from this method.
        2. PUT the image binary directly to ``upload_url`` with the matching Content-Type header.
        3. Call PATCH /v1/salons/me/staff/{staff_id} with { "photo_url": public_url } to record it.

        Args:
            actor: Authenticated owner/staff profile.
            staff_id: ID of the staff member whose photo is being uploaded.
            content_type: MIME type of the image.
            filename: Original filename; used only to derive the file extension.
            bucket: R2 bucket name (read from settings in the router).

        Returns:
            Dict with keys: upload_url, public_url, expires_in.

        Note:
            ``storage_gateway`` is always a fully configured ``R2StorageGateway``
            when called from the router — ``get_storage_gateway()`` validates R2
            env vars at dependency-injection time before this method is reached.
        """
        self._assert_owner_workspace(actor)
        assert self.storage_gateway is not None, "storage_gateway is required for staff photo upload"

        salon = await self.get_my_salon(actor)
        salon_id = str(salon["id"])

        ext = _upload_extension(filename, content_type)
        # Use a new key so a failed/replayed upload cannot replace a published photo.
        staff = await self.repository.list_owner_staff(actor.id)
        if not any(str(member["id"]) == staff_id for member in staff):
            raise NotFoundError("Staff member not found in this salon")
        object_key = f"staff-photos/{salon_id}/{staff_id}/{uuid.uuid4().hex}.{ext}"

        upload_url = await self.storage_gateway.get_upload_url(bucket, object_key, content_type)
        public_url = self.storage_gateway.get_public_url(bucket, object_key)
        return _upload_result(upload_url, public_url)

    async def list_holidays(self, actor: Profile) -> list[dict[str, Any]]:
        """List salon holidays."""

        await assert_approved_workspace(self.repository, actor)
        self._assert_owner_workspace(actor)
        return await self.repository.list_holidays(actor.id)

    async def create_holiday(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create a salon holiday."""

        await assert_approved_workspace(self.repository, actor)
        self._assert_owner_workspace(actor)
        affected = await self.repository.preview_closure(
            actor.id,
            {"kind": "holiday", "holiday_date": values["holiday_date"]},
        )
        if affected:
            raise ConflictError(
                "Holiday affects active bookings; preview and confirm the closure first"
            )
        return await self.repository.create_holiday(actor.id, values)

    async def delete_holiday(self, actor: Profile, holiday_id: str) -> None:
        """Soft-delete a holiday owned by the actor's salon."""

        await assert_approved_workspace(self.repository, actor)
        self._assert_owner_workspace(actor)
        await self.repository.delete_holiday(actor.id, holiday_id)

    async def list_services(self, actor: Profile) -> list[dict[str, Any]]:
        """List owner services."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_owner_services(actor.id)

    async def create_service(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create owner service."""

        self._assert_owner_workspace(actor)
        await self._validate_service_photo(actor, values)
        return await self.repository.create_owner_service(actor.id, values)

    async def update_service(
        self, actor: Profile, service_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update owner service."""

        self._assert_owner_workspace(actor)
        if values.get("photo_url"):
            await self.repository.lock_media_url(values["photo_url"])
            services = await self.repository.list_owner_services(actor.id)
            current = next((service for service in services if str(service["id"]) == service_id), None)
            if current is None or values["photo_url"] != current.get("photo_url"):
                await self._validate_service_photo(actor, values)
        return await self.repository.update_owner_service(actor.id, service_id, values)

    async def _validate_service_photo(self, actor: Profile, values: dict[str, Any]) -> None:
        """Use the configured media base and the existing salon upload namespace."""

        photo_url = values.get("photo_url")
        if photo_url is None:
            return
        await self._validate_salon_media(actor, photo_url)

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
        # There is no staff-specific upload grant until the member exists.
        # A supplied create photo may use this salon's validated gallery namespace.
        await self._validate_salon_media(
            actor, values.get("photo_url"), ImagePolicy(settings.image_staff_dimension, settings.image_photo_max_bytes),
        )
        return await self.repository.create_owner_staff(actor.id, values)

    async def update_staff(
        self, actor: Profile, staff_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update owner staff."""

        self._assert_owner_workspace(actor)
        if values.get("photo_url"):
            await self.repository.lock_media_url(values["photo_url"])
            members = await self.repository.list_owner_staff(actor.id)
            current = next((member for member in members if str(member["id"]) == staff_id), None)
            if current is None:
                raise NotFoundError("Staff member not found")
            if values["photo_url"] != current.get("photo_url"):
                salon = await self.get_my_salon(actor)
                await validate_media_reference(
                    self.repository, self.storage_gateway, values["photo_url"],
                    f"staff-photos/{salon['id']}/{staff_id}/",
                )
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

        await assert_approved_workspace(self.repository, actor)
        self._assert_owner_workspace(actor)
        return await self.repository.list_blocked_slots(actor.id)

    async def create_blocked_slot(
        self, actor: Profile, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a staff-scoped or salon-wide blocked slot."""

        await assert_approved_workspace(self.repository, actor)
        self._assert_owner_workspace(actor)
        affected = await self.repository.preview_closure(
            actor.id,
            {
                "kind": "leave",
                "staff_id": values.get("staff_id"),
                "start_datetime": values["start_datetime"],
                "end_datetime": values["end_datetime"],
            },
        )
        if affected:
            raise ConflictError(
                "Blocked time affects active bookings; preview and confirm the closure first"
            )
        return await self.repository.create_blocked_slot(actor.id, values)

    async def delete_blocked_slot(self, actor: Profile, slot_id: str) -> None:
        """Delete a blocked slot.

        Blocked slots have no is_active column in the schema, so this is a
        hard delete — the schema intentionally treats them as ephemeral entries.
        """

        await assert_approved_workspace(self.repository, actor)
        self._assert_owner_workspace(actor)
        await self.repository.delete_blocked_slot(actor.id, slot_id)


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

    async def create_booking(
        self,
        actor: Profile,
        values: dict[str, Any],
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Create booking through the database function."""

        if values.get("source") == "manual_walkin":
            await assert_approved_workspace(self.repository, actor)
        if values.get("source") == "manual_walkin" and actor.role not in {Role.owner, Role.staff}:
            raise ForbiddenError("Manual walk-in bookings require salon workspace access")
        if values.get("source") == "manual_walkin":
            await assert_approved_workspace(self.repository, actor)
            salon = await self.repository.get_workspace_salon(actor.id)
            if salon is None or str(salon["id"]) != str(values["salon_id"]):
                raise ForbiddenError("You can create walk-in bookings only for your own salon")
        if values.get("source") == "app" and actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer app bookings require customer or owner access")
        if values.get("payment_preference") in {"pay_full", "pay_advance"} and not self.online_payments_enabled:
            raise ConflictError("Online payment coming soon.")
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
        booking_status: str | None = None,
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
            booking_status=booking_status,
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

    async def approve(
        self,
        actor: Profile,
        booking_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Approve a booking and notify the customer."""

        await assert_approved_workspace(self.repository, actor)
        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
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
        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
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
        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
        kwargs = {"idempotency_key": idempotency_key} if idempotency_key else {}
        booking = await self.repository.update_booking_status(actor.id, booking_id, "completed", **kwargs)
        if background_tasks is not None:
            background_tasks.add_task(
                self._notify_customer, booking, "Visit Complete",
                "Thank you for your visit!", "booking_completed"
            )
        return booking

    async def mark_attendance(self, actor: Profile, booking_id: str, *, no_show: bool, idempotency_key: str | None) -> dict:
        await assert_approved_workspace(self.repository, actor)
        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
        return await self.repository.update_booking_status(actor.id, booking_id,
            "no_show" if no_show else "checked_in", idempotency_key=idempotency_key)

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

        reason_labels = {
            "schedule_conflict": "Schedule conflict",
            "found_better": "Found a better option",
            "personal_emergency": "Personal emergency",
            "booked_by_mistake": "Booked by mistake",
            "service_not_needed": "Service no longer needed",
            "other": "Other reason",
        }
        label = reason_labels.get(
            reason_code,
            reason_code.replace("_", " ").capitalize() if reason_code else None,
        )
        cancellation_reason = (
            f"{label} — {reason_text}" if label and reason_text else label or reason_text
        )

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
        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")
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
        if not is_owner_or_staff(actor):
            raise ForbiddenError("Salon workspace access required")

        # Build human-readable label from the structured code.
        _reason_labels: dict[str, str] = {
            "barber_unavailable": "Barber unavailable",
            "salon_emergency": "Salon emergency",
            "overbooking": "Overbooking",
            "customer_no_show": "Customer no-show",
            "equipment_issue": "Equipment issue",
            "other": "Other reason",
        }
        label = _reason_labels.get(reason_code, reason_code.replace("_", " ").capitalize())
        cancellation_reason = f"{label} — {reason_text}" if reason_text else label

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
        except Exception:
            _log.warning("Failed to send notification for booking %s", booking_id)


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

    async def mark_all_read(self, actor: Profile) -> int:
        """Mark all unread notifications owned by the actor."""

        return await self.repository.mark_all_notifications_read(actor.id)

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
