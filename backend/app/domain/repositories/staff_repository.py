"""Staff repository port."""

from typing import Any, Protocol


class StaffRepository(Protocol):
    """Persistence port for staff, staff-service assignments, languages, and blocked slots."""

    async def list_owner_staff(self, actor_id: str) -> list[dict[str, Any]]:
        """Return all staff (active and inactive) for the actor's salon."""

    async def create_owner_staff(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Insert a staff row for the actor's salon."""

    async def update_owner_staff(
        self, actor_id: str, staff_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a staff row. Raises NotFoundError if not owned by actor."""

    async def deactivate_owner_staff(
        self, actor_id: str, staff_id: str
    ) -> dict[str, Any]:
        """Soft-delete a staff member (is_active = False)."""

    async def assign_staff_service(
        self, actor_id: str, staff_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Upsert a staff_services row with optional duration/price overrides."""

    async def list_staff_service_languages(
        self, actor_id: str, staff_id: str, staff_service_id: str
    ) -> list[dict[str, Any]]:
        """Return languages for a staff service assignment."""

    async def set_staff_service_languages(
        self,
        actor_id: str,
        staff_id: str,
        staff_service_id: str,
        language_codes: list[str],
    ) -> list[dict[str, Any]]:
        """Replace language assignments for a staff service (idempotent)."""

    async def list_blocked_slots(self, actor_id: str) -> list[dict[str, Any]]:
        """Return blocked slots for the actor's salon."""

    async def create_blocked_slot(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Insert a blocked_slots row (staff-scoped or salon-wide)."""

    async def delete_blocked_slot(self, actor_id: str, slot_id: str) -> None:
        """Hard-delete a blocked slot. Raises NotFoundError if not owned by actor."""
