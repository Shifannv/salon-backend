"""Dormant subscription provider (``SUBSCRIPTION_PROVIDER=none``): refuses every operation."""

from collections.abc import Mapping

from app.application.ports.subscription_provider import (
    ProviderOrder,
    ProviderPaymentObservation,
    ProviderRefund,
    ProviderSubscriptionEvent,
    SubscriptionClientConfig,
    SubscriptionOrderRequest,
    SubscriptionProvider,
)
from app.core.exceptions import PaymentProviderNotConfiguredError
from app.domain.value_objects.money import Money

_MESSAGE = "Subscription billing is not available yet"


def _refuse() -> PaymentProviderNotConfiguredError:
    return PaymentProviderNotConfiguredError(_MESSAGE)


class NullSubscriptionProvider(SubscriptionProvider):
    @property
    def provider_name(self) -> str:
        return "none"

    def client_config(self) -> SubscriptionClientConfig:
        raise _refuse()

    async def create_period_order(self, request: SubscriptionOrderRequest) -> ProviderOrder:
        raise _refuse()

    async def fetch_order(self, order_ref: str) -> ProviderOrder | None:
        raise _refuse()

    async def find_order_by_receipt(self, receipt: str) -> ProviderOrder | None:
        raise _refuse()

    async def fetch_order_payments(self, order_ref: str) -> list[ProviderPaymentObservation]:
        raise _refuse()

    async def fetch_payment(self, payment_ref: str) -> ProviderPaymentObservation | None:
        raise _refuse()

    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        raise _refuse()

    def parse_event(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> ProviderSubscriptionEvent:
        raise _refuse()

    def verify_client_callback(self, order_ref: str, payment_ref: str, signature: str) -> bool:
        raise _refuse()

    async def refund(
        self, payment_ref: str, amount: Money, idempotency_key: str, reason: str | None = None
    ) -> ProviderRefund:
        raise _refuse()
