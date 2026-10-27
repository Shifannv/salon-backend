"""Subscription API schemas — admin only."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

BillingIntervalLiteral = Literal["monthly", "quarterly", "semiannual", "yearly"]
SubscriptionStatusLiteral = Literal[
    "pending", "trialing", "active", "past_due", "cancelled", "expired", "suspended"
]


class PlanPriceSetRequest(BaseModel):
    """The price one salon pays for one plan, instead of the plan's normal price."""

    price_amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class PlanPriceResponse(BaseModel):
    salon_id: str
    plan_id: str
    plan_code: str
    price_amount: Decimal = Field(max_digits=10, decimal_places=2)
    default_price_amount: Decimal = Field(max_digits=10, decimal_places=2)
    set_by: str | None = None
    updated_at: datetime

    @field_validator("salon_id", "plan_id", "set_by", mode="before")
    @classmethod
    def stringify_ids(cls, v: object) -> str | None:
        return str(v) if v is not None else None


class PlanResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    tier: int
    ranking_weight: int
    price_amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str
    billing_interval: str
    features: dict[str, Any] = Field(default_factory=dict)
    tax_inclusive: bool | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, v: object) -> str:
        return str(v) if v is not None else v


class PlanCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    tier: int = Field(default=0, ge=0)
    ranking_weight: int = Field(default=0, ge=0, le=100000)
    price_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    billing_interval: BillingIntervalLiteral = "monthly"


class PlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    tier: int | None = Field(default=None, ge=0)
    ranking_weight: int | None = Field(default=None, ge=0, le=100000)
    price_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    billing_interval: BillingIntervalLiteral | None = None
    is_active: bool | None = None


class SubscriptionResponse(BaseModel):
    id: str
    salon_id: str
    plan_id: str
    plan_code: str | None = None
    plan_name: str | None = None
    plan_tier: int | None = None
    plan_ranking_weight: int | None = None
    status: SubscriptionStatusLiteral
    starts_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
    expires_at: datetime | None = None
    grace_period_end: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "salon_id", "plan_id", mode="before")
    @classmethod
    def stringify_ids(cls, v: object) -> str | None:
        return str(v) if v is not None else None


class ManualSubscriptionCreateRequest(BaseModel):
    """Manual/test activation — admin only."""

    salon_id: str
    plan_id: str
    status: Literal["pending", "trialing", "active", "past_due"] = "pending"
    starts_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


class SubscriptionEventResponse(BaseModel):
    id: str
    salon_subscription_id: str | None = None
    provider_name: str | None = None
    event_type: str
    processing_status: str
    received_at: datetime
    processed_at: datetime | None = None
    error_message: str | None = None

    @field_validator("id", "salon_subscription_id", mode="before")
    @classmethod
    def stringify_ids(cls, v: object) -> str | None:
        return str(v) if v is not None else None
