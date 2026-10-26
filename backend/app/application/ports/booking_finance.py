"""Provider-independent terminal obligation and manual approval persistence."""

from decimal import Decimal
from typing import Any, Protocol


class BookingFinanceGateway(Protocol):
    async def statement(self, booking_id: str, actor_id: str, *, admin: bool) -> dict[str, Any]: ...

    async def command(self, booking_id: str, version: int, key: str, action: str, amount: Decimal, reference: str) -> None: ...
