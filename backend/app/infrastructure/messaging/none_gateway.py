"""Default gateway: sends nothing. Used until a provider is approved and tested."""

import logging

from app.application.ports.messaging_gateway import OutboundMessage, SendOutcome

logger = logging.getLogger(__name__)


class NoneMessagingGateway:
    async def send(self, message: OutboundMessage) -> SendOutcome:
        # Never log the recipient or the text: both can identify a customer.
        logger.info("messaging disabled: %s message not sent", message.channel)
        return SendOutcome(accepted=False, reason="provider_disabled")
