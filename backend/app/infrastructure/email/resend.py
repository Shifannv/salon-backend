"""Resend API adapter with bounded calls and no payload/key logging."""

import hashlib

import httpx

from app.core.exceptions import ServiceUnavailableError
from app.core.telemetry import measure_external


class ResendEmailGateway:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport

    @property
    def enabled(self):
        return bool(self.settings.resend_api_key and self.settings.resend_api_key.get_secret_value()
                    and self.settings.resend_from_email and self.settings.resend_domain_verified)

    @measure_external("resend")
    async def send(self, *, recipient, subject, body, event_key):
        if not self.enabled:
            raise ServiceUnavailableError("Email delivery is not configured")
        key = "email-" + hashlib.sha256(event_key.encode()).hexdigest()
        try:
            async with httpx.AsyncClient(timeout=10, transport=self.transport) as client:
                response = await client.post("https://api.resend.com/emails", headers={
                    "Authorization": "Bearer " + self.settings.resend_api_key.get_secret_value(),
                    "Idempotency-Key": key,
                }, json={"from": self.settings.resend_from_email, "to": [recipient],
                         "subject": subject, "text": body})
            if response.is_error:
                raise ServiceUnavailableError("Email provider request failed")
            message_id = response.json().get("id")
            if not isinstance(message_id, str) or not message_id:
                raise ServiceUnavailableError("Email provider response is invalid")
            return message_id
        except (httpx.HTTPError, ValueError) as exc:
            raise ServiceUnavailableError("Email provider is unavailable") from exc
