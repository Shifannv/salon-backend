"""Resolve the owner-subscription billing provider.

The ONLY place that reads ``subscription_provider`` to pick an adapter. Entirely independent
of ``PaymentGatewayResolver``: booking collection and subscription billing are enabled,
credentialed and failing independently.
"""

from functools import lru_cache

from app.application.ports.subscription_provider import SubscriptionProvider
from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.exceptions import PaymentProviderNotConfiguredError
from app.infrastructure.adapter_loader import load_adapter
from app.infrastructure.subscriptions.null import NullSubscriptionProvider


def build_subscription_provider(settings: Settings) -> SubscriptionProvider:
    provider = settings.subscription_provider
    if provider == "none":
        return NullSubscriptionProvider()
    module = load_adapter(
        "app.infrastructure.subscriptions",
        provider,
        misconfigured="Subscription provider is misconfigured",
        not_installed="Subscription adapter is not installed",
    )
    return module.create_provider(settings)


class SubscriptionProviderResolver:
    def __init__(self, settings: Settings, provider: SubscriptionProvider | None = None) -> None:
        self._settings = settings
        self._provider = provider

    @property
    def enabled(self) -> bool:
        return self._settings.subscription_provider != "none"

    @property
    def provider_name(self) -> str:
        return self._settings.subscription_provider

    @property
    def grace_days(self) -> int | None:
        return self._settings.subscription_grace_days

    def resolve(self) -> SubscriptionProvider:
        """The provider for NEW orders (``Null`` and refusing when dormant)."""

        if self._provider is None:
            self._provider = build_subscription_provider(self._settings)
        return self._provider

    def for_provider(self, provider: str | None) -> SubscriptionProvider:
        """Provider that HOLDS existing money; never substituted."""

        if not self.enabled or not provider or provider != self.provider_name:
            raise PaymentProviderNotConfiguredError(
                "The provider that holds this subscription payment is not enabled"
            )
        return self.resolve()


@lru_cache
def get_subscription_resolver() -> SubscriptionProviderResolver:
    return SubscriptionProviderResolver(default_settings)
