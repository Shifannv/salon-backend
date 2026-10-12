"""Subscription domain entities — provider-agnostic, pure Python."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class SubscriptionStatus(StrEnum):
    pending = "pending"
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    cancelled = "cancelled"
    expired = "expired"
    suspended = "suspended"


TERMINAL_STATUSES = frozenset({
    SubscriptionStatus.expired,
    SubscriptionStatus.cancelled,
    SubscriptionStatus.suspended,
})

NON_TERMINAL_STATUSES = frozenset(SubscriptionStatus) - TERMINAL_STATUSES


class SubscriptionEventType(StrEnum):
    subscription_started = "subscription_started"
    subscription_renewed = "subscription_renewed"
    payment_failed = "payment_failed"
    subscription_cancelled = "subscription_cancelled"
    subscription_expired = "subscription_expired"
    payment_refunded = "payment_refunded"
    chargeback_created = "chargeback_created"


class EventProcessingStatus(StrEnum):
    received = "received"
    processing = "processing"
    processed = "processed"
    failed = "failed"


@dataclass(frozen=True, slots=True)
class SubscriptionPlan:
    id: str
    code: str
    name: str
    description: str | None
    tier: int
    ranking_weight: int
    price_amount: Decimal
    currency: str
    billing_interval: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SalonSubscription:
    id: str
    salon_id: str
    plan_id: str
    status: SubscriptionStatus
    starts_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancelled_at: datetime | None
    expires_at: datetime | None
    grace_period_end: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SubscriptionEvent:
    id: str
    salon_subscription_id: str | None
    provider_name: str | None
    provider_event_reference: str | None
    event_type: str
    payload_hash: str | None
    received_at: datetime
    processed_at: datetime | None
    processing_status: EventProcessingStatus
    error_message: str | None


class BillingInterval(StrEnum):
    """Allowed ``subscription_plans.billing_interval`` values (CHECK-enforced in 0030)."""

    monthly = "monthly"
    quarterly = "quarterly"
    semiannual = "semiannual"
    yearly = "yearly"


class BillingStatus(StrEnum):
    """Lifecycle of one purchase attempt (``subscription_billing_records.status``)."""

    created = "created"
    authorized = "authorized"
    paid = "paid"
    failed = "failed"
    expired = "expired"
    refunded = "refunded"
    partially_refunded = "partially_refunded"


OPEN_BILLING_STATUSES = frozenset({BillingStatus.created, BillingStatus.authorized})
# A server-verified payment exists for these (money was taken).
PAID_BILLING_STATUSES = frozenset(
    {BillingStatus.paid, BillingStatus.partially_refunded, BillingStatus.refunded}
)


class EntitlementState(StrEnum):
    """Backend-derived answer to "may this salon use the paid benefit right now?"."""

    none = "none"  # never purchased / pending without a paid period
    active = "active"  # inside a paid period
    cancelled_paid_through = "cancelled_paid_through"  # renewal cancelled, access remains
    grace = "grace"  # period ended, inside the configured grace window
    expired = "expired"  # nothing left
    suspended = "suspended"  # admin suspended: never entitled


@dataclass(frozen=True, slots=True)
class Entitlement:
    active: bool
    state: EntitlementState
    paid_through: datetime | None
    grace_ends_at: datetime | None


def derive_entitlement(
    *,
    status: str | None,
    period_start: datetime | None,
    period_end: datetime | None,
    grace_end: datetime | None,
    now: datetime,
) -> Entitlement:
    """Pure mirror of the SQL function ``is_subscription_promotion_active``.

    Grace is read from the STORED ``grace_period_end`` (set when a period is paid), never
    recomputed from today's configuration, so a later config change cannot rewrite history.
    Expiry, cancellation and history viewing are never gated by this: it only answers
    whether the approved premium benefit (promotion eligibility) applies.
    """

    if status is None or period_end is None:
        return Entitlement(False, EntitlementState.none, None, None)
    if status == SubscriptionStatus.suspended:
        return Entitlement(False, EntitlementState.suspended, period_end, None)
    if status in {SubscriptionStatus.pending, SubscriptionStatus.expired}:
        state = EntitlementState.none if status == SubscriptionStatus.pending else (
            EntitlementState.expired
        )
        return Entitlement(False, state, period_end, None)
    started = period_start is not None and now >= period_start
    if status == SubscriptionStatus.cancelled:
        if now < period_end:
            return Entitlement(True, EntitlementState.cancelled_paid_through, period_end, None)
        return Entitlement(False, EntitlementState.expired, period_end, None)
    if status in {SubscriptionStatus.active, SubscriptionStatus.trialing}:
        if started and now < period_end:
            return Entitlement(True, EntitlementState.active, period_end, grace_end)
        if now >= period_end and grace_end is not None and now < grace_end:
            return Entitlement(True, EntitlementState.grace, period_end, grace_end)
        return Entitlement(False, EntitlementState.expired, period_end, grace_end)
    if status == SubscriptionStatus.past_due:
        if grace_end is not None and now < grace_end:
            return Entitlement(True, EntitlementState.grace, period_end, grace_end)
        return Entitlement(False, EntitlementState.expired, period_end, grace_end)
    return Entitlement(False, EntitlementState.none, period_end, None)
