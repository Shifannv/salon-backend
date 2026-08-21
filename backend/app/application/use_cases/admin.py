"""Super-admin use cases."""

from typing import Any

from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.core.exceptions import ForbiddenError, ValidationError
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
    ) -> list[dict[str, Any]]:
        """List all salons (including inactive) for the admin view."""
        self._assert_admin(actor)
        return await self.repository.admin_list_salons(search, limit, offset)

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
