"""Owner subscription billing API schemas. Money is Decimal (rupees, 2 dp), serialised as a string."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

BillingStatusLiteral = Literal[
    "created", "authorized", "paid", "failed", "expired", "refunded", "partially_refunded"
]


class SubscriptionConfigResponse(BaseModel):
    enabled: bool
    provider: str | None = None
    mode: Literal["one_time"] = "one_time"
    renewal: Literal["manual"] = "manual"
    native_purchase_allowed: Literal[False] = False
    public_key: str | None = None
    currency: str = "INR"
    # The website page where a plan is bought; null until the operator configures one.
    checkout_url: str | None = None


class PurchasablePlanResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    tier: int
    # The price this salon pays: an admin-set price when there is one, else the plan price.
    price_amount: Decimal = Field(max_digits=10, decimal_places=2)
    default_price_amount: Decimal = Field(max_digits=10, decimal_places=2)
    custom_price: bool = False
    # Salon-specific saving vs this plan's normal price. Separate from duration savings below.
    offer_discount_percent: int | None = None
    currency: str
    billing_interval: Literal["monthly", "quarterly", "semiannual", "yearly"]
    features: dict[str, Any] = Field(default_factory=dict)
    tax_inclusive: bool | None = None
    # Per-month cost for multi-month plans, used to show "₹X/mo". Null for monthly plans.
    monthly_equivalent: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    # % saving vs the same tier's 1-month effective price, rounded to the nearest whole percent
    # (rupee-rounded prices make 10% read as 9.98%). Null for monthly plans.
    discount_percent: int | None = None


class BillingPaymentResponse(BaseModel):
    id: str
    plan_code: str
    status: BillingStatusLiteral
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str
    billing_interval: str
    tax_amount: Decimal | None = None
    tax_inclusive: bool | None = None
    refunded_amount: Decimal = Field(max_digits=10, decimal_places=2)
    order_ref: str | None = None
    receipt: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    expires_at: datetime
    paid_at: datetime | None = None
    applied_at: datetime | None = None
    payment_verified: bool
    entitlement_applied: bool
    created_at: datetime


class PlanSummary(BaseModel):
    id: str
    code: str
    name: str
    tier: int


class SubscriptionStateResponse(BaseModel):
    provider_enabled: bool
    status: str | None = None
    plan: PlanSummary | None = None
    entitlement_active: bool
    entitlement_state: Literal[
        "none", "active", "cancelled_paid_through", "grace", "expired", "suspended"
    ]
    features: dict[str, Any] = Field(default_factory=dict)
    paid_through: datetime | None = None
    grace_ends_at: datetime | None = None
    in_grace: bool
    renewal: Literal["manual"] = "manual"
    cancelled: bool
    cancelled_at: datetime | None = None
    latest_payment: BillingPaymentResponse | None = None
    open_checkout: BillingPaymentResponse | None = None
    verification: str | None = None


class CheckoutRequest(BaseModel):
    plan_id: UUID


class CheckoutResponse(BaseModel):
    billing_id: str
    provider: str
    order_ref: str
    receipt: str
    plan_id: str
    plan_code: str
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str
    billing_interval: str
    expires_at: datetime
    client_payload: dict[str, Any]


class VerifyRequest(BaseModel):
    order_ref: str = Field(min_length=1, max_length=100)
    # Optional client-side checkout result: a hint about which payment to fetch, never proof.
    payment_ref: str | None = Field(default=None, max_length=100)
    signature: str | None = Field(default=None, max_length=200)


class FeatureSwitch(BaseModel):
    enabled: bool
    source: Literal["plan", "override", "none"]
    # Paid plans that include the feature, e.g. ["premium"].
    plans: list[Literal["growth", "premium"]] = Field(default_factory=list)


class PlanTierContent(BaseModel):
    headline: str = ""
    description: str = ""
    bullets: list[str] = Field(default_factory=list)


class AccessStateResponse(BaseModel):
    accepts_new_bookings: bool
    subscription_wall: bool
    wall_messages: list[str] = Field(default_factory=list)
    trial_started_at: datetime | None = None
    trial_ends_at: datetime | None = None
    trial_booking_limit: int | None = None
    trial_bookings_counted: int | None = None
    access_state: Literal["not_subscribed", "subscribed", "subscribed_growth", "subscribed_premium"]
    entitlement_active: bool
    entitlement_state: str
    features: dict[str, Any] = Field(default_factory=dict)
    # Per-feature switch set by the super admin: {key: {"enabled": bool, "source": "plan"|"override"|"none"}}.
    feature_access: dict[str, FeatureSwitch] | None = None
    plan_content: dict[str, PlanTierContent] | None = None
    paid_through: datetime | None = None
    grace_ends_at: datetime | None = None
    source: Literal["subscription"] = "subscription"
