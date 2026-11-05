"""Barber/owner app use cases."""

import uuid
from typing import Any

from app.application.ports.image_processor import ImagePolicy
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media_publication import validate_media_reference
from app.application.use_cases.owner_setup import (
    PAYOUT_FIELDS,
    build_setup_status,
    mask_payout_account,
    validate_payout_account,
)
from app.application.use_cases.upload_helpers import _upload_extension, _upload_result
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.domain.entities.profile import Profile
from app.domain.services.authorization import is_owner, is_owner_or_staff
from app.infrastructure.db.repositories.platform_repository import PlatformRepository


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
        return _upload_result(upload_url, public_url, self.storage_gateway.get_result_url(upload_url))

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
        return _upload_result(upload_url, public_url, self.storage_gateway.get_result_url(upload_url))

    async def list_holidays(self, actor: Profile) -> list[dict[str, Any]]:
        """List salon holidays."""

        await assert_approved_workspace(self.repository, actor)
        return await self.repository.list_holidays(actor.id)

    async def create_holiday(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        """Create a salon holiday."""

        await assert_approved_workspace(self.repository, actor)
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
        await self.repository.delete_holiday(actor.id, holiday_id)

    async def list_services(self, actor: Profile) -> list[dict[str, Any]]:
        """List owner services."""

        self._assert_owner_workspace(actor)
        return await self.repository.list_owner_services(actor.id)

    async def create_services(self, actor: Profile, items: list[dict]) -> list[dict]:
        self._assert_owner_workspace(actor)
        for item in items:
            await self._validate_service_photo(actor, item)
        return await self.repository.create_owner_services(actor.id, items)

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

    async def get_staff_capabilities(self, actor: Profile, staff_id: str) -> dict:
        self._assert_owner_workspace(actor)
        return await self.repository.get_staff_capabilities(actor.id, staff_id)

    async def set_staff_capabilities(self, actor: Profile, staff_id: str, values: dict) -> dict:
        self._assert_owner_workspace(actor)
        return await self.repository.set_staff_capabilities(actor.id, staff_id, values)

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
        return await self.repository.list_blocked_slots(actor.id)

    async def create_blocked_slot(
        self, actor: Profile, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a staff-scoped or salon-wide blocked slot."""

        await assert_approved_workspace(self.repository, actor)
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
        await self.repository.delete_blocked_slot(actor.id, slot_id)
