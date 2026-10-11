"""Resolve which payment gateway serves a salon.

This is the ONLY place that reads ``payment_provider``/``payment_settlement_model`` to pick
an adapter. Call sites ask ``resolve(salon_id)`` and never branch on the provider, so a
future "customer pays the salon directly" arrives as a different adapter *instance* here,
not as a different call site.
"""

import importlib
import re
from functools import lru_cache

from app.application.ports.payment_gateway import PaymentGateway
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.exceptions import PaymentProviderNotConfiguredError
from app.domain.entities.payment import SettlementModel
from app.infrastructure.payments.null import NullPaymentGateway

_MODULE_NAME = re.compile(r"[a-z][a-z0-9_]*")


def build_gateway(settings: Settings) -> PaymentGateway:
    """Instantiate the configured adapter by module name (``none`` -> dormant)."""

    provider = settings.payment_provider
    if provider == "none":
        return NullPaymentGateway()
    if not _MODULE_NAME.fullmatch(provider):
        raise PaymentProviderNotConfiguredError("Payment provider is misconfigured")
    try:
        module = importlib.import_module(f"app.infrastructure.payments.{provider}")
    except ModuleNotFoundError as exc:
        raise PaymentProviderNotConfiguredError("Payment provider adapter is not installed") from exc
    return module.create_gateway(settings)


class PaymentGatewayResolver:
    """Per-salon gateway lookup. Today every salon shares one platform-level gateway."""

    def __init__(self, settings: Settings, gateway: PaymentGateway | None = None) -> None:
        self._settings = settings
        self._gateway = gateway

    @property
    def provider(self) -> str:
        return self._settings.payment_provider

    @property
    def enabled(self) -> bool:
        return self.provider != "none"

    @property
    def settlement_model(self) -> SettlementModel:
        return SettlementModel(self._settings.payment_settlement_model)

    def resolve(self, salon_id: str | None = None) -> PaymentGateway:
        """Return the gateway for ``salon_id`` (unused until per-salon credentials exist)."""

        if self._gateway is None:
            self._gateway = build_gateway(self._settings)
        return self._gateway


@lru_cache
def get_payment_resolver() -> PaymentGatewayResolver:
    """Process-wide resolver built from the cached settings."""

    return PaymentGatewayResolver(default_settings)
