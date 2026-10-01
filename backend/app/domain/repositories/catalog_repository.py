"""Catalog repository port."""

from typing import Any, Protocol


class CatalogRepository(Protocol):
    """Persistence port for the global service catalog (super-admin curated)."""

    async def list_categories(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        """Return service categories, optionally including deactivated ones."""

    async def get_category(self, category_id: str) -> dict[str, Any]:
        """Return one category. Raises NotFoundError if absent."""

    async def create_category(self, values: dict[str, Any]) -> dict[str, Any]:
        """Insert a service_categories row."""

    async def update_category(
        self, category_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service_categories row. Raises NotFoundError if absent."""

    async def deactivate_category(self, category_id: str) -> dict[str, Any]:
        """Soft-delete a category (is_active = False)."""

    async def list_subcategories(
        self, category_id: str, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        """Return subcategories for a category."""

    async def get_subcategory(self, subcategory_id: str) -> dict[str, Any]:
        """Return one subcategory. Raises NotFoundError if absent."""

    async def create_subcategory(self, values: dict[str, Any]) -> dict[str, Any]:
        """Insert a service_subcategories row."""

    async def update_subcategory(
        self, subcategory_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service_subcategories row. Raises NotFoundError if absent."""

    async def deactivate_subcategory(self, subcategory_id: str) -> dict[str, Any]:
        """Soft-delete a subcategory (is_active = False)."""

    async def list_available_languages(self) -> list[dict[str, Any]]:
        """Return all language reference rows."""

    async def list_owner_services(self, actor_id: str) -> list[dict[str, Any]]:
        """Return all services (active and inactive) for the actor's salon."""

    async def create_owner_service(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Insert a services row for the actor's salon."""

    async def update_owner_service(
        self, actor_id: str, service_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a services row. Raises NotFoundError if not owned by actor."""

    async def deactivate_owner_service(
        self, actor_id: str, service_id: str
    ) -> dict[str, Any]:
        """Soft-delete a service (is_active = False)."""
