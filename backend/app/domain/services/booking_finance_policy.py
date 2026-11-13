"""Approved U08 calculations for explicitly versioned bookings.

This module does not activate a policy, rewrite legacy snapshots, move money, or
approve a payout. Application/SQL commands must enforce ownership, immutable
booking policy selection, ledger limits, locking and provider release gates.
Any prospective rule change needs a new version; preserve this version's rules.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.value_objects.money import round_money

POLICY_VERSION = "u08-2026-10-23-v1"
_ZERO = Decimal("0.00")
_EARLY_FEE = Decimal("20.00")
_PLATFORM_RATE = Decimal("0.30")


def _amount(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError("Money must be a finite non-negative Decimal")
    return round_money(value)


def _remaining(start: datetime, now: datetime) -> timedelta:
    if not isinstance(start, datetime) or not isinstance(now, datetime):
        raise TypeError("Appointment and decision instants must be datetimes")
    if start.utcoffset() is None or now.utcoffset() is None:
        raise ValueError("Appointment and decision instants must be timezone-aware")
    return start.astimezone(UTC) - now.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Allocation:
    """Internal accounting result; never serialize wholesale to owner responses."""

    salon_share: Decimal
    platform_share: Decimal
    platform_shortfall: Decimal
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True, slots=True)
class CancellationQuote:
    """Internal quote, not proof that a refund or payout has happened."""

    penalty: Decimal
    customer_refund: Decimal
    retained_pool: Decimal
    salon_share: Decimal
    platform_share: Decimal
    platform_shortfall: Decimal
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True, slots=True)
class ServiceChangeQuote:
    """Payment obligations only; no reservation, verification or commit is implied."""

    service_total: Decimal
    total_obligation: Decimal
    additional_online_payment: Decimal
    pay_at_salon_due: Decimal
    customer_refund: Decimal = _ZERO
    policy_version: str = POLICY_VERSION


def service_change_quote(
    new_service_total: Decimal, retained_payment: Decimal, *, payment_preference: str,
) -> ServiceChangeQuote:
    """Quote using an authoritative SQL service total and reconciled retained funds.

    Prepaid cheaper changes retain the payment, including on later changes; an
    upgrade needs only the shortfall above those retained funds. Unpaid salon
    collection uses the new price. Partial/advance or already-collected salon
    payments need separate ledger treatment and must not enter the unpaid path.

    Callers must bind verified additional funds to the exact booking/change version
    before atomically committing a newly available slot. A quote is not evidence
    that payment succeeded, that a slot is held, or that a booking may be changed.
    """
    total, retained = _amount(new_service_total), _amount(retained_payment)
    if payment_preference == "pay_at_salon" and retained == _ZERO:
        return ServiceChangeQuote(total, total, _ZERO, total)
    if payment_preference != "pay_full":
        raise ValueError("booking_change_payment_state_unsupported")
    obligation = max(total, retained)
    return ServiceChangeQuote(total, obligation, obligation - retained, _ZERO)


def cancellation_quote(
    captured: Decimal,
    appointment_start: datetime,
    decision_at: datetime,
    provider_costs: Decimal,
    *,
    salon_caused: bool = False,
) -> CancellationQuote:
    """Quote U08 on its captured policy base, before prior-refund ledger capping.

    ``salon_caused`` is only for an authorized pre-check-in salon/admin cancellation.
    Callers must not use it to decide the unresolved checked-in monetary remedy.
    Actual provider costs affect internal allocation only, never the promised refund.
    """
    captured, costs = _amount(captured), _amount(provider_costs)
    remaining = _remaining(appointment_start, decision_at)
    if salon_caused:
        penalty = _ZERO
    elif remaining >= timedelta(hours=48):
        penalty = min(_EARLY_FEE, captured)
    elif remaining >= timedelta(hours=12):
        penalty = round_money(captured * Decimal("0.05"))
    elif remaining > timedelta(hours=4):
        penalty = round_money(captured * Decimal("0.35"))
    else:
        penalty = captured
    pool = max(_ZERO, penalty - costs)
    platform = round_money(pool * _PLATFORM_RATE)
    return CancellationQuote(
        penalty=penalty,
        customer_refund=captured - penalty,
        retained_pool=pool,
        salon_share=pool - platform,
        platform_share=platform,
        platform_shortfall=max(_ZERO, costs - penalty),
    )


def completed_service_allocation(captured: Decimal, provider_costs: Decimal) -> Allocation:
    """Zero service commission; completion and finance approval are separate gates."""
    captured, costs = _amount(captured), _amount(provider_costs)
    return Allocation(
        salon_share=max(_ZERO, captured - costs),
        platform_share=_ZERO,
        platform_shortfall=max(_ZERO, costs - captured),
    )


def validate_customer_change(
    appointment_start: datetime, decision_at: datetime, committed_reschedules: int,
    *, changes_time: bool = True,
) -> None:
    """Validate timing/count only; SQL must secure the new slot and commit the count."""
    if type(committed_reschedules) is not int or committed_reschedules < 0:
        raise ValueError("Committed reschedules must be a non-negative integer")
    if _remaining(appointment_start, decision_at) <= timedelta(hours=4):
        raise ValueError("booking_change_cutoff")
    if changes_time and committed_reschedules >= 2:
        raise ValueError("booking_change_limit")


def validate_no_show(
    appointment_start: datetime, decision_at: datetime, reason: str | None,
    warning_deadline: datetime | None = None,
) -> str:
    """Validate the grace period and normalize the required explicit reason.

    The grace is ten minutes after the start, or the salon's own warning once it has run out.
    """
    warned = warning_deadline is not None and decision_at >= warning_deadline
    if not warned and _remaining(appointment_start, decision_at) > -timedelta(minutes=10):
        raise ValueError("no_show_grace_period")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("no_show_reason_required")
    return reason.strip()
