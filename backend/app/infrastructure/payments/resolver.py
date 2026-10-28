"""Resolve which payment gateway serves a salon, a stored payment row or a webhook.

This is the ONLY place that reads ``payment_provider``/``payment_settlement_model`` to pick an
adapter. Call sites ask for a gateway and never branch on the provider name, so a future
"customer pays the salon directly" arrives as a different adapter *instance* here, not as a
different call site.

Gateways are kept in a registry keyed by provider name:

* ``resolve()`` returns the gateway for NEW bookings (the configured booking provider).
* ``for_provider(name)`` returns the gateway for an EXISTING row/refund/webhook by the provider
  recorded on it, so an order is never refunded or reconciled through another provider. A
  provider that is not independently enabled is refused, never substituted.
* ``webhook_gateways(name)`` returns the verifiers allowed for ``POST /webhooks/{name}``, each
  tagged with the business domain its own secret authorises.
"""

from functools import lru_cache
from types import ModuleType

from app.application.ports.payment_gateway import PaymentGateway
from app.application.ports.payment_provider import PayoutProvider, ProviderFeeReconciler
from app.application.ports.subscription_provider import SubscriptionProvider
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.exceptions import (
    NotFoundError,
    PaymentCapabilityError,
    PaymentProviderNotConfiguredError,
)
from app.domain.entities.payment import SettlementModel, WebhookDomain
from app.infrastructure.adapter_loader import load_adapter
from app.infrastructure.payments.null import NullPaymentGateway
from app.infrastructure.subscriptions.resolver import build_subscription_provider


def _adapter_module(provider: str) -> ModuleType:
    return load_adapter(
        "app.infrastructure.payments",
        provider,
        misconfigured="Payment provider is misconfigured",
        not_installed="Payment provider adapter is not installed",
    )


def build_gateway(settings: Settings) -> PaymentGateway:
    """Instantiate the configured booking adapter by module name (``none`` -> dormant)."""

    provider = settings.payment_provider
    if not settings.booking_payments_enabled:
        return NullPaymentGateway()
    return _adapter_module(provider).create_gateway(settings)


class PaymentGatewayResolver:
    """Gateway registry. Today every salon shares one platform-level booking gateway."""

    def __init__(
        self,
        settings: Settings,
        gateway: PaymentGateway | None = None,
        gateways: dict[str, PaymentGateway] | None = None,
        subscription_provider_port: SubscriptionProvider | None = None,
    ) -> None:
        self._settings = settings
        self._gateway = gateway
        self._extra = dict(gateways or {})
        self._subscription_port = subscription_provider_port

    # ------------------------------------------------------------- identity
    @property
    def provider(self) -> str:
        """The configured booking provider (``none`` when dormant)."""

        return self._settings.payment_provider

    @property
    def enabled(self) -> bool:
        return self._settings.booking_payments_enabled

    @property
    def subscription_provider(self) -> str | None:
        return self._settings.subscription_webhook_provider

    @property
    def settlement_model(self) -> SettlementModel:
        return SettlementModel(self._settings.payment_settlement_model)

    # ------------------------------------------------------------- lookups
    def resolve(self, salon_id: str | None = None) -> PaymentGateway:
        """Gateway for NEW payments (unused ``salon_id`` until per-salon credentials exist)."""

        if self._gateway is None:
            self._gateway = build_gateway(self._settings)
        return self._gateway

    def for_provider(self, provider: str | None) -> PaymentGateway:
        """Gateway for money that already exists at ``provider``. Never substitutes."""

        if not provider or not self.enabled:
            raise PaymentProviderNotConfiguredError("Online payment is not available yet")
        if provider == self.provider:
            return self.resolve()
        if provider in self._extra:
            return self._extra[provider]
        raise PaymentProviderNotConfiguredError(
            "The payment provider that holds this payment is not enabled"
        )

    def payout_provider(self) -> PayoutProvider:
        """Optional capability; payment/split support never implies payout support."""
        gateway = self.resolve()
        if not isinstance(gateway, PayoutProvider):
            raise PaymentCapabilityError("The provider does not support payouts")
        return gateway

    def fee_reconciler(self) -> ProviderFeeReconciler:
        gateway = self.resolve()
        if not isinstance(gateway, ProviderFeeReconciler):
            raise PaymentCapabilityError("The provider does not support fee reconciliation")
        return gateway

    def webhook_gateways(
        self, provider: str
    ) -> list[tuple[PaymentGateway | SubscriptionProvider, WebhookDomain]]:
        """Verifiers (gateway, domain) allowed to authorise ``POST /webhooks/{provider}``.

        Raises ``NotFoundError`` unless ``provider`` is independently enabled for payments
        and/or subscriptions. Each verifier checks only its own secret/algorithm.
        """

        found: list[tuple[PaymentGateway | SubscriptionProvider, WebhookDomain]] = []
        if self.enabled and provider == self.provider:
            found.append((self.resolve(), WebhookDomain.payment))
        if provider == self.subscription_provider:
            # Verified by the SUBSCRIPTION port with its own webhook secret, never a booking key.
            if self._subscription_port is None:
                self._subscription_port = build_subscription_provider(self._settings)
            found.append((self._subscription_port, WebhookDomain.subscription))
        if not found:
            raise NotFoundError("Not found")
        return found


@lru_cache
def get_payment_resolver() -> PaymentGatewayResolver:
    """Process-wide resolver built from the cached settings."""

    return PaymentGatewayResolver(default_settings)
