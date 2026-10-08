"""Salon repository port."""

from typing import Any, Protocol


class SalonRepository(Protocol):
    """Persistence port for salon, image, and holiday access."""

    async def get_owner_salon(self, actor_id: str) -> dict[str, Any]:
        """Return the salon owned by the actor. Raises NotFoundError if absent."""

    async def update_owner_salon(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update owner-editable salon fields. Raises NotFoundError if absent."""

    async def complete_owner_salon(
        self, actor_id: str, values: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create/update the owner's salon and set profile_completed = True."""

    async def list_salon_images(self, salon_id: str) -> list[dict[str, Any]]:
        """Return images for a salon ordered by sort_order."""

    async def create_salon_image(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Insert a salon_images row for the actor's salon."""

    async def update_salon_image(
        self, actor_id: str, image_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a salon image. Raises NotFoundError if not owned by actor."""

    async def list_holidays(self, actor_id: str) -> list[dict[str, Any]]:
        """Return holidays for the actor's salon."""

    async def create_holiday(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Insert a salon_holidays row for the actor's salon."""

    async def delete_holiday(self, actor_id: str, holiday_id: str) -> None:
        """Soft-delete a holiday owned by the actor's salon."""

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
        include_services: bool = False,
    ) -> list[dict[str, Any]]:
        """Return active, completed, public salons."""

    async def get_public_salon(self, salon_id: str) -> dict[str, Any]:
        """Return public salon detail. Raises NotFoundError if not active/completed."""

    async def list_public_services(self, salon_id: str) -> list[dict[str, Any]]:
        """Return active services for a salon visible to customers."""

    async def get_salon_by_qr(self, qr_token: str) -> dict[str, Any]:
        """Return salon info by QR token. Raises NotFoundError if invalid."""
