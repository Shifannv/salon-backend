"""Super-admin use cases."""

from typing import Any

from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.salon_approval_repository import SalonApprovalRepository
from app.core.exceptions import ConflictError, ForbiddenError, ValidationError
from app.domain.entities.profile import Profile
from app.domain.services.authorization import is_super_admin
from app.infrastructure.db.repositories.platform_repository import PlatformRepository


class AdminUseCases:
    """Super-admin salon and owner management."""

    def __init__(
        self,
        repository: PlatformRepository,
        auth_admin: AuthAdminGateway,
    ) -> None:
        self.repository = repository
        self.approval_repository: SalonApprovalRepository = repository
        self.auth_admin = auth_admin

    def _assert_admin(self, actor: Profile) -> None:
        if not is_super_admin(actor):
            raise ForbiddenError("Super admin access required")

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

    async def _assert_reviewable(self, salon_id: str) -> None:
        salon = await self.approval_repository.admin_get_salon(salon_id)
        if not salon["is_active"] or not salon["profile_completed"]:
            raise ConflictError("Only active salons with completed onboarding can be reviewed")

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
        self, actor: Profile, salon_id: str
    ) -> dict[str, Any]:
        """Approve a pending salon — owner's workspace becomes fully accessible.

        Only salons that have completed onboarding (``profile_completed = true``)
        can be approved.  Approving an already-approved salon is idempotent.
        """
        self._assert_admin(actor)
        await self._assert_reviewable(salon_id)
        return await self.approval_repository.admin_set_salon_approval(salon_id, "approved", actor.id, None)

    async def reject_salon(
        self, actor: Profile, salon_id: str, rejection_reason: str
    ) -> dict[str, Any]:
        """Reject a pending (or previously approved) salon with a reason.

        The owner sees the reason on their pending-approval screen and may fix
        issues and re-submit.  Rejection does NOT ban the owner account.
        """
        self._assert_admin(actor)
        if not rejection_reason.strip():
            raise ValidationError("rejection_reason must not be blank")
        await self._assert_reviewable(salon_id)
        return await self.approval_repository.admin_set_salon_approval(
            salon_id, "rejected", actor.id, rejection_reason.strip()
        )


class CatalogAdminUseCases:
    """Super-admin service catalog management."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def _assert_admin(self, actor: Profile) -> None:
        if not is_super_admin(actor):
            raise ForbiddenError("Super admin access required")

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
        return await self.repository.create_category(values)

    async def update_category(
        self, actor: Profile, category_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service category."""
        self._assert_admin(actor)
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
        return await self.repository.create_subcategory(values)

    async def update_subcategory(
        self, actor: Profile, subcategory_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service subcategory."""
        self._assert_admin(actor)
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
