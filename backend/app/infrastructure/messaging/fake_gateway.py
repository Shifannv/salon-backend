"""In-process fake provider for local/test. Never touches the network."""

from itertools import count

from app.application.ports.messaging_gateway import OutboundMessage, SendOutcome


class FakeMessagingGateway:
    def __init__(self, outcome: SendOutcome | None = None, raises: Exception | None = None) -> None:
        self._outcome = outcome
        self._raises = raises
        self._ids = count(1)
        self._by_key: dict[str, SendOutcome] = {}
        self.attempts: list[OutboundMessage] = []
        self.sent: list[OutboundMessage] = []

    async def send(self, message: OutboundMessage) -> SendOutcome:
        self.attempts.append(message)
        if self._raises is not None:
            raise self._raises
        if message.idempotency_key in self._by_key:
            return self._by_key[message.idempotency_key]
        outcome = self._outcome or SendOutcome(accepted=True, provider_message_id=f"fake-{next(self._ids)}")
        self._by_key[message.idempotency_key] = outcome
        if outcome.accepted:
            self.sent.append(message)
        return outcome
