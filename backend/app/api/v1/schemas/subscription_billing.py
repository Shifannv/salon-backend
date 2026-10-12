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


class PurchasablePlanResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    tier: int
    price_amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str
    billing_interval: Literal["monthly", "quarterly", "semiannual", "yearly"]
    features: dict[str, Any] = Field(default_factory=dict)
    tax_inclusive: bool | None = None


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


class AccessStateResponse(BaseModel):
    access_state: Literal["not_subscribed", "subscribed", "subscribed_growth", "subscribed_premium"]
    entitlement_active: bool
    entitlement_state: str
    features: dict[str, Any] = Field(default_factory=dict)
    paid_through: datetime | None = None
    grace_ends_at: datetime | None = None
    source: Literal["subscription"] = "subscription"
