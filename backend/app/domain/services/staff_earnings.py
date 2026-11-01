"""Staff earnings money rules. Pure functions on integer paise; no database, no clock.

Decisions this follows: F07 (a rule is picked staff+service, then staff, then service, then the
salon default, else nothing: there is never an implicit rate) and F10 plus the Phase 1 design (the
rule is frozen when the service completes, and a refund reverses its matching share of the earning
as a new entry; nothing is ever edited). Cash and UPI are salon-level receipts and play no part here:
an earning depends only on the service line's value and the rule in force when it completed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

COMMISSION_TYPES = ("NONE", "FIXED_PER_SERVICE", "PERCENT_OF_SERVICE_VALUE")
BASIS_POINTS = 10_000


@dataclass(frozen=True)
class CommissionRule:
    """One version of one rule. ``staff_id`` / ``service_id`` of ``None`` mean "any"."""

    id: str
    staff_id: str | None
    service_id: str | None
    version: int
    commission_type: str
    rate_basis_points: int | None
    fixed_amount_paise: int | None
    effective_from: datetime


def _specificity(rule: CommissionRule) -> int:
    """3 staff+service, 2 staff-wide, 1 service-wide, 0 salon default (F07)."""

    if rule.staff_id is not None and rule.service_id is not None:
        return 3
    if rule.staff_id is not None:
        return 2
    if rule.service_id is not None:
        return 1
    return 0


def select_rule(
    rules: list[CommissionRule], staff_id: str, service_id: str, at: datetime
) -> CommissionRule | None:
    """The rule that applied to this staff member and service at ``at``, or ``None`` (earns nothing).

    Only rules already in force at ``at`` count, so a past service keeps the rule it was completed
    under. Within the most specific scope that has any rule, the latest start (then the highest
    version) wins. The order the rules are passed in never matters.
    """

    candidates = [
        rule
        for rule in rules
        if rule.effective_from <= at
        and rule.staff_id in (None, staff_id)
        and rule.service_id in (None, service_id)
    ]
    if not candidates:
        return None
    best = max(_specificity(rule) for rule in candidates)
    scoped = [rule for rule in candidates if _specificity(rule) == best]
    return max(scoped, key=lambda rule: (rule.effective_from, rule.version, rule.id))


def _half_up(numerator: int, denominator: int) -> int:
    """``numerator / denominator`` rounded half up, in integers only (non-negative inputs)."""

    return (2 * numerator + denominator) // (2 * denominator)


def earned_amount(rule: CommissionRule | None, service_value_paise: int) -> int:
    """What one service earns its staff member. Never negative, never more than the service cost."""

    if rule is None or service_value_paise <= 0 or rule.commission_type == "NONE":
        return 0
    if rule.commission_type == "FIXED_PER_SERVICE":
        return min(rule.fixed_amount_paise or 0, service_value_paise)
    if rule.commission_type == "PERCENT_OF_SERVICE_VALUE":
        return min(_half_up(service_value_paise * (rule.rate_basis_points or 0), BASIS_POINTS), service_value_paise)
    raise ValueError(f"unknown commission type {rule.commission_type!r}")


def reversal_due(*, earned: int, service_value: int, refunded_to_line: int, already_reversed: int) -> int:
    """How much more of an earning a refund must reverse, given what was reversed before.

    The earning is reversed in proportion to how much of the line has been refunded in total, rounded
    half up, never above the earning and never below what was already reversed. Seeing the same refund
    twice returns 0, and a refund that arrives in pieces ends exactly where one big refund would.
    """

    if earned <= 0 or service_value <= 0 or refunded_to_line <= 0:
        return 0
    refunded = min(refunded_to_line, service_value)
    target = min(_half_up(earned * refunded, service_value), earned)
    return max(target - already_reversed, 0)


def split_refund_across_lines(refund_paise: int, line_values: list[int]) -> list[int]:
    """Share a payment refund between the booking's service lines in proportion to their value.

    The shares always add up to the refund exactly (largest remainder; a tie goes to the earlier
    line), no line gets more than it cost, and a refund above the total is capped at the total.
    """

    total = sum(line_values)
    if refund_paise <= 0 or total <= 0:
        return [0] * len(line_values)
    refund = min(refund_paise, total)
    shares = [refund * value // total for value in line_values]
    leftover = refund - sum(shares)
    by_remainder = sorted(range(len(line_values)), key=lambda i: (-(refund * line_values[i] % total), i))
    for index in by_remainder:
        if leftover == 0:
            break
        if shares[index] < line_values[index]:
            shares[index] += 1
            leftover -= 1
    return shares


def collected_by_staff(
    lines: list[tuple[str, int]], *, cash_paise: int, upi_paise: int
) -> dict[str, tuple[int, int]]:
    """What was collected on each person's services: (cash, non-cash) per staff id (F19).

    ``lines`` are the booking's completed service lines as (staff id, value in paise). Each payment
    method is shared between the lines in proportion to their value, so the shares add up to what the
    customer paid (never more than the booking total). The result is a view of the salon's own receipts,
    not anyone's pay: it plays no part in commission.
    """

    values = [value for _, value in lines]
    cash = split_refund_across_lines(cash_paise, values)
    upi = split_refund_across_lines(upi_paise, values)
    shares: dict[str, tuple[int, int]] = {}
    for (staff_id, _), cash_share, upi_share in zip(lines, cash, upi, strict=True):
        before_cash, before_upi = shares.get(staff_id, (0, 0))
        shares[staff_id] = (before_cash + cash_share, before_upi + upi_share)
    return shares
