"""Customer "service completed" message, sent only when every guard allows it.

Off by default and unreachable in production today: ``MESSAGING_PROVIDER`` is ``none`` and no
real adapter exists. The guards run in a fixed order and each refusal is a plain reason string,
never an exception, so completing a booking can never fail because a message could not be sent.

Idempotency: one attempt per booking, ever. A provider refusal is not retried and not counted
against the quota; a duplicate call is dropped before the provider is contacted.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.application.ports.messaging_gateway import MessagingGateway, OutboundMessage
from app.domain.services.message_templates import UnsafeMessageError, render
from app.domain.services.messaging_quota import QuotaWindow, has_quota, month_window

logger = logging.getLogger(__name__)


class UsageStore(Protocol):
    async def used_in_window(self, salon_id: str, window: QuotaWindow) -> int: ...

    async def claim(self, key: str) -> bool:
        """True the first time a key is seen, False for every repeat."""

    async def record_accepted(
        self, salon_id: str, window: QuotaWindow, key: str, provider_message_id: str | None
    ) -> None: ...


@dataclass(frozen=True)
class SendDecision:
    sent: bool
    reason: str


def _e164(raw: str) -> str | None:
    digits = re.sub(r"[\s()-]", "", raw)
    if re.fullmatch(r"\+\d{10,15}", digits):
        return digits
    if re.fullmatch(r"[6-9]\d{9}", digits):  # a bare Indian mobile number
        return f"+91{digits}"
    return None


class CompletionMessageService:
    def __init__(
        self, gateway: MessagingGateway, usage: UsageStore, *, enabled: bool, monthly_cap: int
    ) -> None:
        self._gateway = gateway
        self._usage = usage
        self._enabled = enabled
        self._cap = monthly_cap

    async def notify_completed(
        self,
        *,
        salon_id: str,
        salon_name: str,
        timezone: str,
        booking_id: str,
        customer_name: str,
        customer_phone: str | None,
        service_name: str,
        entitled: bool,
        now: datetime,
    ) -> SendDecision:
        if not self._enabled:
            return SendDecision(False, "disabled")
        if not entitled:
            return SendDecision(False, "not_entitled")
        if not customer_phone:
            return SendDecision(False, "no_phone")
        recipient = _e164(customer_phone)
        if recipient is None:
            return SendDecision(False, "invalid_phone")
        try:
            text = render(
                "service_completed",
                first_name=(customer_name.split() or ["there"])[0],
                service=service_name,
                salon=salon_name,
            )
        except UnsafeMessageError:
            return SendDecision(False, "unsafe_content")

        window = month_window(now, timezone)
        if not has_quota(await self._usage.used_in_window(salon_id, window), self._cap):
            return SendDecision(False, "quota_exhausted")

        key = f"completion:{booking_id}"
        if not await self._usage.claim(key):
            return SendDecision(False, "duplicate")

        try:
            outcome = await self._gateway.send(
                OutboundMessage(channel="whatsapp", recipient=recipient, text=text, idempotency_key=key)
            )
        except Exception:  # a provider fault must never undo or block a completed booking
            logger.exception("completion message provider error for booking %s", booking_id)
            return SendDecision(False, "provider_error")
        if not outcome.accepted:
            return SendDecision(False, outcome.reason or "provider_rejected")
        await self._usage.record_accepted(salon_id, window, key, outcome.provider_message_id)
        return SendDecision(True, "sent")
