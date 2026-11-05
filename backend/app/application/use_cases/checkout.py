"""Checkout validation using the existing database slot authority."""

from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.core.exceptions import ForbiddenError, SlotUnavailableError
from app.domain.entities.profile import Profile, Role
from app.domain.services.checkout import checkout_quote, online_checkout_available


class BookingCheckoutUseCases:
    def __init__(
        self, repository: Any, resolver: Any, *, policy_version: str = "customer_processing_v1"
    ) -> None:
        self.repository = repository
        self.resolver = resolver
        self.policy_version = policy_version

    async def quote(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer access required")
        salon = await self.repository.checkout_salon(values["salon_id"])
        start = values["start_datetime"]
        day = start.astimezone(ZoneInfo(salon["timezone"])).date()
        if values.get("segments"):
            slots = await self.repository.get_visit_slots(str(values["salon_id"]), day,
                [{"staff_id":str(part["staff_id"]),"service_ids":[str(s) for s in part["service_ids"]]} for part in values["segments"]])
            slot = next((s for s in slots if s["slot_start"] == start), None)
            if slot is None:
                raise SlotUnavailableError("Selected slot is no longer available")
            services = {"amount": Decimal(str(slot["total_price"]))}
        else:
            services = await self.repository.quote_services(values["salon_id"], values["staff_id"], values["service_ids"])
            if not await self.repository.quoted_slot_available(values["staff_id"], day, services["duration"], start):
                raise SlotUnavailableError("Selected slot is no longer available")
        online = online_checkout_available(self.resolver.enabled, self.policy_version) and salon["accepting_bookings"]
        return {
            **checkout_quote(services["amount"], values["payment_mode"], policy_version=self.policy_version),
            "accepts_bookings": salon["accepting_bookings"],
            "payment_options": ["PAY_AT_SALON", "PAY_ONLINE"] if online else ["PAY_AT_SALON"],
            "online_payment_available": online,
            "online_payment_unavailable_reason": None if online else "Online payment coming soon.",
        }
