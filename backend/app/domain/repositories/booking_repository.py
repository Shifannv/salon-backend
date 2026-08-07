"""Booking repository port."""

from collections.abc import Iterable
from datetime import date
from typing import Any, Protocol


class BookingRepository(Protocol):
    """Persistence port for bookings and availability.

    The critical constraint: ALL slot computation and booking creation must
    delegate to the Postgres functions ``get_available_slots`` and
    ``create_booking``. Python must never compute availability or insert
    directly into ``bookings`` or ``booking_services``.
    """

    async def get_available_slots(
        self, staff_id: str, booking_date: date, service_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Delegate to the ``get_available_slots`` Postgres function.

        Returns a list of {slot_start, slot_end} dicts in UTC.
        """

    async def get_service_duration_sum(
        self, staff_id: str, service_ids: Iterable[str]
    ) -> int:
        """Return the effective total duration for the given staff + service combination.

        Used by ``get_available_slots`` internally.
        """

    async def create_booking(self, values: dict[str, Any]) -> dict[str, Any]:
        """Delegate to the ``create_booking`` Postgres function.

        Raises SlotUnavailableError (→ HTTP 409) if the slot is gone.
        Never inserts directly into ``bookings`` or ``booking_services``.
        """

    async def list_bookings(
        self, actor_id: str, role: str
    ) -> list[dict[str, Any]]:
        """Return role-scoped bookings.

        - customer: own bookings only
        - owner/staff: bookings for their salon
        - super_admin: all bookings
        """

    async def get_booking(
        self, booking_id: str, actor_id: str | None
    ) -> dict[str, Any] | None:
        """Return one booking visible to actor_id. Returns None if not visible."""

    async def update_booking_status(
        self,
        actor_id: str,
        booking_id: str,
        status: str,
        *,
        rejection_reason: str | None = None,
        customer_only: bool = False,
    ) -> dict[str, Any]:
        """Update booking status with actor-scoped authorization.

        If customer_only is True, only matches if customer_id == actor_id.
        Otherwise, matches if actor_id owns the salon or is the assigned staff.
        Raises NotFoundError if not visible.
        """

    async def record_payment(
        self, actor_id: str, booking_id: str, payment_method: str
    ) -> dict[str, Any]:
        """Record booking payment (owner/staff only)."""
