"""Pick the payout transfer adapter by the configured provider name.

The ONLY place that reads ``payout_provider``. The adapter module is imported by name, so nothing
provider-specific (and no HTTP client) is loaded unless payouts are switched on.
"""

from app.application.ports.payout_transfer import PayoutTransferGateway
from app.core.config import Settings
from app.infrastructure.adapter_loader import load_adapter


def build_payout_gateway(settings: Settings) -> PayoutTransferGateway | None:
    """The configured adapter, or None when automatic payout is off (``PAYOUT_PROVIDER=none``)."""

    provider = settings.payout_provider
    if provider == "none":
        return None
    module = load_adapter(
        "app.infrastructure.payouts",
        provider,
        misconfigured="Payout provider is misconfigured",
        not_installed="Payout provider adapter is not installed",
    )
    return module.create_gateway(settings)
