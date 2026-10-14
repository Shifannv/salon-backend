"""Checkout validation using the existing database slot authority."""

from zoneinfo import ZoneInfo

from app.core.exceptions import ForbiddenError, SlotUnavailableError
from app.domain.entities.profile import Role
from app.domain.services.checkout import checkout_quote


class BookingCheckoutUseCases:
    def __init__(self, repository, resolver):
        self.repository = repository
        self.resolver = resolver

    async def quote(self, actor, values):
        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer access required")
        salon = await self.repository.checkout_salon(values["salon_id"])
        services = await self.repository.quote_services(values["salon_id"], values["staff_id"], values["service_ids"])
        start = values["start_datetime"]
        day = start.astimezone(ZoneInfo(salon["timezone"])).date()
        if not await self.repository.quoted_slot_available(values["staff_id"], day, services["duration"], start):
            raise SlotUnavailableError("Selected slot is no longer available")
        online = self.resolver.enabled and salon["accepting_bookings"]
        return {
            **checkout_quote(services["amount"], values["payment_mode"]),
            "accepts_bookings": salon["accepting_bookings"],
            "payment_options": ["PAY_AT_SALON", "PAY_ONLINE"] if online else ["PAY_AT_SALON"],
            "online_payment_available": online,
            "online_payment_unavailable_reason": None if online else "Online payment coming soon.",
        }
