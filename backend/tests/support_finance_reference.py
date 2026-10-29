"""Reference arithmetic for the owner-finance DESIGN (Phase 1). Not application code.

It pins the money rules in docs/finance/FINANCE_PHASE1_DESIGN.md so a later implementation can be
checked against the same numbers. All amounts are integer paise; nothing here touches a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

BASIS_POINTS = 10_000


def half_up_div(numerator: int, denominator: int) -> int:
    """Integer division rounding halves up, for non-negative operands."""
    if denominator <= 0 or numerator < 0:
        raise ValueError("denominator must be positive and numerator non-negative")
    return (numerator * 2 + denominator) // (denominator * 2)


@dataclass(frozen=True)
class CommissionPolicy:
    """The policy frozen onto an earning when the service completes."""

    commission_type: str  # NONE | FIXED_PER_SERVICE | PERCENT_OF_SERVICE_VALUE
    rate_basis_points: int | None = None
    fixed_amount_paise: int | None = None

    def __post_init__(self) -> None:
        kind = self.commission_type
        if kind == "NONE":
            if self.rate_basis_points is not None or self.fixed_amount_paise is not None:
                raise ValueError("NONE carries no rate or amount")
        elif kind == "FIXED_PER_SERVICE":
            if self.fixed_amount_paise is None or self.fixed_amount_paise < 0 or self.rate_basis_points is not None:
                raise ValueError("FIXED_PER_SERVICE needs only a non-negative fixed amount")
        elif kind == "PERCENT_OF_SERVICE_VALUE":
            rate = self.rate_basis_points
            if rate is None or not 0 <= rate <= BASIS_POINTS or self.fixed_amount_paise is not None:
                raise ValueError("PERCENT_OF_SERVICE_VALUE needs only a 0-10000 basis-point rate")
        else:
            raise ValueError(f"unknown commission type {kind!r}")


def earned_commission(policy: CommissionPolicy, service_value_paise: int) -> int:
    if service_value_paise < 0:
        raise ValueError("service value cannot be negative")
    if policy.commission_type == "NONE":
        return 0
    if policy.commission_type == "FIXED_PER_SERVICE":
        return policy.fixed_amount_paise or 0
    return half_up_div(service_value_paise * (policy.rate_basis_points or 0), BASIS_POINTS)


def refund_reversals(earned: int, service_value_paise: int, cumulative_refunds: list[int]) -> list[int]:
    """Reversal for each successive refund of one service, proportional to money refunded so far.

    Each reversal is the cumulative proportional amount minus what was already reversed, so the
    sum never drifts and never exceeds the earning, however the refunds are split.
    """
    if service_value_paise <= 0:
        raise ValueError("service value must be positive")
    reversals: list[int] = []
    reversed_so_far = 0
    refunded_so_far = 0
    for refund in cumulative_refunds:
        if refund <= 0:
            raise ValueError("refunds must be positive")
        refunded_so_far += refund
        if refunded_so_far > service_value_paise:
            raise ValueError("refunds exceed the service value")
        target = half_up_div(earned * refunded_so_far, service_value_paise)
        reversals.append(target - reversed_so_far)
        reversed_so_far = target
    return reversals


def local_day_bounds(local_date: date, timezone: str) -> tuple[datetime, datetime]:
    """The half-open UTC interval [start, end) covering one salon-local calendar day."""
    zone = ZoneInfo(timezone)
    start = datetime(local_date.year, local_date.month, local_date.day, tzinfo=zone)
    end = datetime.combine(local_date + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return start.astimezone(UTC), end.astimezone(UTC)


def expected_closing_cash(
    *,
    opening_cash: int,
    cash_collected: int,
    cash_refunds: int,
    cash_expenses: int,
    cash_adjustments_in: int = 0,
    cash_adjustments_out: int = 0,
) -> int:
    return (
        opening_cash + cash_collected - cash_refunds - cash_expenses
        + cash_adjustments_in - cash_adjustments_out
    )


def close_difference(expected: int, actual: int, reason: str | None) -> int:
    """Actual minus expected; a non-zero difference needs a written reason."""
    difference = actual - expected
    if difference != 0 and not (reason or "").strip():
        raise ValueError("difference_reason_required")
    return difference


def net_expense_total(entries: list[dict[str, object]]) -> int:
    """Expenses minus their reversals; a reversal must mirror exactly one earlier expense."""
    expense_ids = {e["id"] for e in entries if e["entry_type"] == "expense"}
    seen: set[object] = set()
    total = 0
    for entry in entries:
        amount = int(entry["amount_paise"])  # type: ignore[arg-type]
        if amount <= 0:
            raise ValueError("amounts must be positive")
        if entry["entry_type"] == "expense":
            total += amount
            continue
        target = entry["reverses_id"]
        if target not in expense_ids:
            raise ValueError("a reversal must reference an expense")
        if target in seen:
            raise ValueError("expense_already_reversed")
        seen.add(target)
        total -= amount
    return total
