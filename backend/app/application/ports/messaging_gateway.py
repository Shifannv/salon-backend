"""Outbound customer/owner messaging port (WhatsApp and SMS). Provider-neutral.

No real provider exists yet: ``MESSAGING_PROVIDER`` defaults to ``none`` and only a fake adapter
is available, for local/test. Resend is transactional email only and is never used here.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

Channel = Literal["whatsapp", "sms"]


@dataclass(frozen=True)
class OutboundMessage:
    channel: Channel
    recipient: str  # E.164, e.g. +919876543210
    text: str  # already rendered from an approved template and checked for private data
    idempotency_key: str


@dataclass(frozen=True)
class SendOutcome:
    """``accepted`` is the provider accepting the message, which is what consumes quota."""

    accepted: bool
    provider_message_id: str | None = None
    reason: str | None = None


class MessagingGateway(Protocol):
    async def send(self, message: OutboundMessage) -> SendOutcome:
        """Send at most once per ``idempotency_key``; never raise for a provider refusal."""
