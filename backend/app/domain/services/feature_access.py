"""Which features a salon can use. Pure functions: the super admin sets a Trial/Growth/Premium
matrix and optional per-salon overrides; this module only combines them.

An override beats the matrix until it expires. A salon with no live trial and no paid
entitlement belongs to no audience, so only overrides can unlock anything for it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Audience = Literal["trial", "growth", "premium"]
AUDIENCES: tuple[Audience, ...] = ("trial", "growth", "premium")
PAID_AUDIENCES: tuple[Audience, ...] = ("growth", "premium")

# Features the backend enforces by name; the catalogue table holds their labels.
SPLIT_BILL = "split_bill"
DAILY_LEDGER = "daily_ledger"
EXPENSES = "expenses"
FINANCE_PAGE = "finance_page"
REPORTS = "reports"
STAFF_EARNINGS = "staff_earnings"
WALLET = "wallet"


@dataclass(frozen=True, slots=True)
class FeatureOverride:
    enabled: bool
    expires_at: datetime | None = None

    def live(self, now: datetime) -> bool:
        return self.expires_at is None or self.expires_at > now


def audience_for(*, entitlement_active: bool, tier: int | None, trial_active: bool) -> Audience | None:
    """The matrix column a salon is read from. A paid plan wins over a trial still running."""

    if entitlement_active:
        return "premium" if tier is not None and tier >= 2 else "growth"
    return "trial" if trial_active else None


def resolve_features(
    *,
    audience: Audience | None,
    matrix: Mapping[str, Mapping[str, bool]],
    overrides: Mapping[str, FeatureOverride],
    now: datetime,
) -> dict[str, dict[str, object]]:
    """``{feature: {"enabled", "source": "plan" | "override" | "none", "plans": [...]}}`` per catalogue key.

    ``plans`` lists the paid plans that include the feature, so a locked screen can say which one to pick.
    """

    resolved: dict[str, dict[str, object]] = {}
    for key, columns in matrix.items():
        plans = [tier for tier in PAID_AUDIENCES if columns.get(tier) is True]
        override = overrides.get(key)
        if override is not None and override.live(now):
            resolved[key] = {"enabled": override.enabled, "source": "override", "plans": plans}
        elif audience is None:
            resolved[key] = {"enabled": False, "source": "none", "plans": plans}
        else:
            resolved[key] = {"enabled": columns.get(audience) is True, "source": "plan", "plans": plans}
    return resolved


def is_enabled(resolved: Mapping[str, Mapping[str, object]], key: str) -> bool:
    """Unknown keys are locked, so a typo in a guard fails closed."""

    return resolved.get(key, {}).get("enabled") is True
