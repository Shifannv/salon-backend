"""The dormant gateway used when no payment provider is configured."""

from collections.abc import Mapping

from app.application.ports.payment_gateway import (
    ClientConfig,
    PaymentCallback,
    PaymentEvent,
    PaymentGateway,
    PaymentIntent,
    PaymentIntentRequest,
    ProviderPayment,
    RefundRequest,
    RefundResult,
    SettlementAccount,
    SettlementAccountRequest,
)
from app.core.exceptions import PaymentProviderNotConfiguredError
from app.domain.entities.payment import GatewayCapability

_MESSAGE = "Online payment is not available yet"


class NullPaymentGateway(PaymentGateway):
    """Answers ``supports() == False`` and refuses everything else with a 503."""

    @property
    def provider_name(self) -> str:
        return "none"

    def supports(self, capability: GatewayCapability) -> bool:
        return False

    def client_config(self) -> ClientConfig:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    async def create_payment_intent(self, request: PaymentIntentRequest) -> PaymentIntent:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    def verify_payment_callback(self, callback: PaymentCallback) -> bool:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    def parse_event(self, raw_body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    async def fetch_payment(
        self, *, payment_ref: str | None = None, order_ref: str | None = None
    ) -> ProviderPayment | None:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    async def refund(self, request: RefundRequest) -> RefundResult:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    async def register_settlement_account(
        self, request: SettlementAccountRequest
    ) -> SettlementAccount:
        raise PaymentProviderNotConfiguredError(_MESSAGE)

    async def get_settlement_account(self, account_ref: str) -> SettlementAccount:
        raise PaymentProviderNotConfiguredError(_MESSAGE)
