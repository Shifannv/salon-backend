"""Payment API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PaymentConfigResponse(BaseModel):
    """What the apps need to decide whether to offer online payment."""

    enabled: bool
    provider: str | None = None
    public_key: str | None = None
    currency: str
    advance_percent: int
    settlement_model: str | None = None


class PaymentIntentRequest(BaseModel):
    """Start an online payment for a booking. The amount is NEVER client supplied."""

    model_config = ConfigDict(extra="forbid")

    purpose: Literal["deposit", "balance", "full"] | None = None


class PaymentIntentResponse(BaseModel):
    """Open payment order plus the opaque payload the checkout SDK needs."""

    payment_id: str
    provider: str
    order_ref: str
    purpose: str
    amount: Decimal
    currency: str
    client_payload: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class PaymentConfirmRequest(BaseModel):
    """Client-side success callback, verified server-side before anything is trusted."""

    model_config = ConfigDict(extra="forbid")

    order_ref: str = Field(min_length=1, max_length=200)
    payment_ref: str = Field(min_length=1, max_length=200)
    signature: str = Field(min_length=1, max_length=400)


class PaymentRefundRequest(BaseModel):
    """Refund a captured online payment (omit amount for the full remainder)."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    reason: str | None = Field(default=None, max_length=500)


class BookingPaymentResponse(BaseModel):
    """One ledger row."""

    id: str
    booking_id: str
    channel: str
    purpose: str
    settlement_model: str
    provider: str | None = None
    method: str | None = None
    instrument: str | None = None
    amount: Decimal
    currency: str
    status: str
    failure_code: str | None = None
    expires_at: datetime | None = None
    captured_at: datetime | None = None
    created_at: datetime


class RefundResponse(BaseModel):
    """One refund."""

    id: str
    payment_id: str
    amount: Decimal
    status: str
    reason: str | None = None
    created_at: datetime
    processed_at: datetime | None = None


class BookingPaymentsResponse(BaseModel):
    """Everything money-related about one booking."""

    booking_id: str
    currency: str
    total_price: Decimal
    deposit_amount: Decimal | None = None
    paid_amount: Decimal
    refunded_amount: Decimal
    payment_status: str
    payment_state: str
    payments: list[BookingPaymentResponse]
    refunds: list[RefundResponse]


class EarningsResponse(BaseModel):
    """Owner earnings derived from the ledger."""

    currency: str
    online_collected: Decimal
    online_refunded: Decimal
    platform_fees: Decimal
    online_net: Decimal
    manual_recorded: Decimal
    online_payment_count: int
    manual_payment_count: int
    note: str


class SettlementAccountResponse(BaseModel):
    """Salon payee account at the provider (split-settlement model only)."""

    provider_enabled: bool
    supported: bool
    onboarding_status: str
    requirements: list[str] = Field(default_factory=list)


class WebhookAckResponse(BaseModel):
    """Acknowledgement of a webhook delivery."""

    status: Literal["accepted", "duplicate", "ignored"]
