"""Business email delivery port. Auth mail remains Supabase Custom SMTP."""

from typing import Protocol


class EmailGateway(Protocol):
    async def send(self, *, recipient: str, subject: str, body: str, event_key: str) -> str:
        """Send once with the provider idempotency key; return only its message identifier."""
