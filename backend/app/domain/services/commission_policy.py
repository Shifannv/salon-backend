"""Which commission rate and base apply to a payment (pure, no I/O).

The super admin sets a platform rate and base, and may give one salon its own rate. A rate in the
environment is only a fallback for installs that have not set one in the admin. Nothing is ever
defaulted: when no rate or no base is known the caller must refuse the payment.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

COMMISSION_BASES = ("online_amount", "booking_total")
MAX_RATE_PERCENT = Decimal("100")


@dataclass(frozen=True)
class CommissionPolicy:
    rate_percent: Decimal
    base: str
    version: str
    #: Where the rate came from: ``salon``, ``platform`` or ``environment``.
    source: str


def resolve_commission_policy(
    *,
    salon_rate: Decimal | None,
    platform_rate: Decimal | None,
    platform_base: str | None,
    platform_version: int,
    env_rate: Decimal | None,
    env_base: str | None,
    env_version: str,
) -> CommissionPolicy | None:
    """Salon rate, else platform rate, else environment rate; the base is the platform's, else the environment's."""

    base = platform_base or env_base
    if salon_rate is not None:
        rate, source = salon_rate, "salon"
    elif platform_rate is not None:
        rate, source = platform_rate, "platform"
    elif env_rate is not None:
        rate, source = env_rate, "environment"
    else:
        return None
    if base is None:
        return None
    version = f"db-{platform_version}" if platform_base is not None else env_version
    if source == "salon":
        version = f"{version}-salon"
    return CommissionPolicy(Decimal(rate), base, version, source)


def check_rate(rate: Decimal) -> Decimal:
    """A percentage between 0 and 100 with at most two decimals, or ``ValueError``."""

    if rate < 0 or rate > MAX_RATE_PERCENT:
        raise ValueError("The commission rate must be between 0 and 100")
    if rate != rate.quantize(Decimal("0.01")):
        raise ValueError("The commission rate can have at most two decimals")
    return rate
