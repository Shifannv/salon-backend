"""Subscription domain entities — provider-agnostic, pure Python."""

from dataclasses import dataclass
from datetime import datetime
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
    price_amount: float
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
