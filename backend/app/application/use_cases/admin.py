"""Super-admin use cases."""

import logging
from typing import Any, Protocol

from fastapi import BackgroundTasks

from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.salon_approval_repository import SalonApprovalRepository
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media_publication import validate_media_reference
from app.core.exceptions import ConflictError, ValidationError
from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_super_admin
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

_log = logging.getLogger(__name__)


class UserNotifier(Protocol):
    """Persist one in-app notification for a user and attempt push delivery."""

    async def __call__(
        self,
        *,
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> None: ...


_MAX_PUSH_REASON_LENGTH = 500  # keeps the provider data payload far below FCM's 4 KB limit


class AdminUseCases:
    """Super-admin salon and owner management."""

    def __init__(
        self,
        repository: PlatformRepository,
        auth_admin: AuthAdminGateway,
        notify_owner: UserNotifier | None = None,
    ) -> None:
        self.repository = repository
        self.approval_repository: SalonApprovalRepository = repository
        self.auth_admin = auth_admin
        self.notify_owner = notify_owner

    def _assert_admin(self, actor: Profile) -> None:
        require_super_admin(actor)

    async def create_salon_owner(
        self,
        actor: Profile,
        email: str,
        password: str,
        full_name: str,
        salon_name: str,
        timezone: str,
    ) -> dict[str, Any]:
        """Create a Supabase Auth user and a salon in one transaction.

        If the DB insert fails, the auth user is banned to avoid orphaned
        auth accounts. The profile row is created by the handle_new_user trigger.
        """
        self._assert_admin(actor)

        created = await self.auth_admin.create_user(
            email=email, password=password, role="owner", full_name=full_name
        )
        try:
            salon = await self.repository.admin_create_salon(
                owner_user_id=created.user_id,
                salon_name=salon_name,
                timezone=timezone,
            )
        except Exception as exc:
            # Roll back the auth user so there are no orphaned accounts.
            await self.auth_admin.ban_user(created.user_id)
            raise ValidationError(
                "Salon creation failed; auth user has been reverted"
            ) from exc
        return salon

    async def list_salons(
        self,
        actor: Profile,
        search: str | None,
        limit: int,
        offset: int,
        approval_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all salons (including inactive) for the admin view."""
        self._assert_admin(actor)
        if approval_status is None:
            return await self.repository.admin_list_salons(search, limit, offset)
        return await self.repository.admin_list_salons(search, limit, offset, approval_status)

    async def get_salon(self, actor: Profile, salon_id: str) -> dict[str, Any]:
        self._assert_admin(actor)
        return await self.approval_repository.admin_get_salon(salon_id)

    async def get_onboarding(self, actor: Profile, salon_id: str) -> dict[str, Any]:
        """Authorize the complete submission before reading private owner data."""
        self._assert_admin(actor)
        return await self.repository.admin_get_onboarding(salon_id)

    async def _assert_reviewable(self, salon_id: str) -> dict[str, Any]:
        salon = await self.approval_repository.admin_get_salon(salon_id)
        if not salon["is_active"] or not salon["profile_completed"]:
            raise ConflictError("Only active salons with completed onboarding can be reviewed")
        return salon

    async def _push_decision(
        self,
        salon: dict[str, Any],
        status: str,
        title: str,
        body: str,
        reason: str | None,
        background_tasks: BackgroundTasks | None,
    ) -> None:
        """Owner push, deferred past the response so a slow provider can't stall the admin."""
        owner_id = salon.get("owner_id")
        if self.notify_owner is None or not owner_id:
            return
        data = {"type": "approval_status", "status": status}
        if reason is not None:
            data["reason"] = reason[:_MAX_PUSH_REASON_LENGTH]
        args = (str(owner_id), title, body, data, salon.get("id"))
        if background_tasks is None:
            await self._send_push(*args)
        else:
            background_tasks.add_task(self._send_push, *args)

    async def _send_push(
        self, owner_id: str, title: str, body: str, data: dict[str, Any], salon_id: Any
    ) -> None:
        """Best-effort delivery; a push problem must never undo (or fail) the decision."""
        notifier = self.notify_owner
        if notifier is None:  # _push_decision already guards this
            return
        try:
            await notifier(
                user_id=owner_id,
                notification_type="approval_status",
                title=title,
                body=body,
                data=data,
            )
        except Exception as exc:
            _log.warning("Approval push failed for salon %s: %s", salon_id, type(exc).__name__)

    async def update_salon(
        self, actor: Profile, salon_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update admin-editable salon fields (name, timezone)."""
        self._assert_admin(actor)
        return await self.repository.admin_update_salon(salon_id, values)

    async def deactivate_salon(
        self, actor: Profile, salon_id: str
    ) -> dict[str, Any]:
        """Soft-delete the salon and ban the owner's Supabase Auth account."""
        self._assert_admin(actor)
        result = await self.repository.admin_deactivate_salon(salon_id)
        owner_id = str(result["owner_id"])
        await self.auth_admin.ban_user(owner_id)
        return result

    async def approve_salon(
        self,
        actor: Profile,
        salon_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Approve a pending salon — owner's workspace becomes fully accessible.

        Only salons that have completed onboarding (``profile_completed = true``)
        can be approved.  Approving an already-approved salon is idempotent.
        """
        self._assert_admin(actor)
        before = await self._assert_reviewable(salon_id)
        updated = await self.approval_repository.admin_set_salon_approval(
            salon_id, "approved", actor.id, None
        )
        if before.get("approval_status") != "approved":
            await self._push_decision(
                before,
                "approved",
                "Your salon is verified 🎉",
                "Customers can now discover and book your salon.",
                None,
                background_tasks,
            )
        return updated

    async def reject_salon(
        self,
        actor: Profile,
        salon_id: str,
        rejection_reason: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Reject a pending (or previously approved) salon with a reason.

        The owner sees the reason on their pending-approval screen and may fix
        issues and re-submit.  Rejection does NOT ban the owner account.
        """
        self._assert_admin(actor)
        if not rejection_reason.strip():
            raise ValidationError("rejection_reason must not be blank")
        reason = rejection_reason.strip()
        before = await self._assert_reviewable(salon_id)
        updated = await self.approval_repository.admin_set_salon_approval(
            salon_id, "rejected", actor.id, reason
        )
        if before.get("approval_status") != "rejected" or before.get("rejection_reason") != reason:
            await self._push_decision(
                before,
                "rejected",
                "Action needed on your salon",
                "Our team left feedback. Open the app to review and resubmit.",
                reason,
                background_tasks,
            )
        return updated


class CatalogAdminUseCases:
    """Super-admin service catalog management."""

    def __init__(self, repository: PlatformRepository, storage_gateway: StorageGateway | None = None) -> None:
        self.repository = repository
        self.storage_gateway = storage_gateway

    async def _validate_image(self, values: dict[str, Any]) -> None:
        # Catalog admins have platform-wide authority, but an image must still
        # come from a validated gallery upload rather than an arbitrary URL.
        await validate_media_reference(self.repository, self.storage_gateway, values.get("image_url"), "salon-images/")

    def _assert_admin(self, actor: Profile) -> None:
        require_super_admin(actor)

    # Categories

    async def list_categories(
        self, actor: Profile, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        """List service categories."""
        self._assert_admin(actor)
        return await self.repository.list_categories(include_inactive)

    async def create_category(
        self, actor: Profile, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a service category."""
        self._assert_admin(actor)
        await self._validate_image(values)
        return await self.repository.create_category(values)

    async def update_category(
        self, actor: Profile, category_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service category."""
        self._assert_admin(actor)
        if values.get("image_url"):
            await self.repository.lock_media_url(values["image_url"])
            current = await self.repository.get_category(category_id)
            if values["image_url"] != current.get("image_url"):
                await self._validate_image(values)
        return await self.repository.update_category(category_id, values)

    async def deactivate_category(
        self, actor: Profile, category_id: str
    ) -> dict[str, Any]:
        """Soft-delete a service category."""
        self._assert_admin(actor)
        return await self.repository.deactivate_category(category_id)

    # Subcategories

    async def list_subcategories(
        self, actor: Profile, category_id: str, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        """List subcategories for a category."""
        self._assert_admin(actor)
        return await self.repository.list_subcategories(category_id, include_inactive)

    async def create_subcategory(
        self, actor: Profile, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a service subcategory."""
        self._assert_admin(actor)
        await self._validate_image(values)
        return await self.repository.create_subcategory(values)

    async def update_subcategory(
        self, actor: Profile, subcategory_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service subcategory."""
        self._assert_admin(actor)
        if values.get("image_url"):
            await self.repository.lock_media_url(values["image_url"])
            current = await self.repository.get_subcategory(subcategory_id)
            if values["image_url"] != current.get("image_url"):
                await self._validate_image(values)
        return await self.repository.update_subcategory(subcategory_id, values)

    async def deactivate_subcategory(
        self, actor: Profile, subcategory_id: str
    ) -> dict[str, Any]:
        """Soft-delete a service subcategory."""
        self._assert_admin(actor)
        return await self.repository.deactivate_subcategory(subcategory_id)

    async def list_available_languages(self) -> list[dict[str, Any]]:
        """List supported languages (public reference data)."""
        return await self.repository.list_available_languages()
