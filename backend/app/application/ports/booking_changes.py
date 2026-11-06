"""Atomic customer booking-change persistence boundary."""

from datetime import date
from typing import Any, Protocol


class BookingChangeGateway(Protocol):
    async def availability(self, booking_id: str, staff_id: str, services: list[str], day: date) -> list[dict[str, Any]]: ...

    async def visit_availability(self, booking_id: str, segments: list[dict[str, Any]], day: date) -> list[dict[str, Any]]: ...

    async def quote(self, booking_id: str, values: dict[str, Any]) -> dict[str, Any]: ...

    async def commit(self, booking_id: str, values: dict[str, Any], key: str) -> dict[str, Any]: ...
