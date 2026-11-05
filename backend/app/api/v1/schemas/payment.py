"""Payment API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, model_validator


class PaymentConfigResponse(BaseModel):
    """What the apps need to decide whether to offer online payment."""

    enabled: bool
    online_payment_available: bool = False
    online_payment_unavailable_reason: str | None = "Online payment coming soon."
    provider: str | None = None
    public_key: str | None = None
    currency: str
    advance_percent: int
    settlement_model: str | None = None
    # 'callback' = POST .../payments/confirm with a signed callback; 'refresh' = POST
    # .../payments/refresh (the backend asks the provider; the SDK callback proves nothing).
    confirmation: str | None = None


from app.api.v1.schemas.booking import VisitSegmentRequest


class BookingQuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    salon_id: UUID
    staff_id: UUID
    service_ids: list[UUID] = Field(min_length=1, max_length=30)
    start_datetime: AwareDatetime
    segments: list[VisitSegmentRequest] | None = Field(default=None, min_length=1, max_length=30)
    payment_mode: Literal["PAY_ONLINE", "PAY_AT_SALON"]


class BookingQuoteResponse(BaseModel):
    checkout_policy_version: str = "customer_processing_v1"
    payment_mode: Literal["PAY_ONLINE", "PAY_AT_SALON"]
    currency: str = "INR"
    service_amount: Decimal
    online_processing_charge_percent: Decimal
    online_processing_charge: Decimal
    total_payable: Decimal
    charge_label: str | None
    instructions: list[str]
    accepts_bookings: bool
    payment_options: list[str]
    online_payment_available: bool
    online_payment_unavailable_reason: str | None


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
    # Required only by providers that sign the client callback; ignored by the others, whose
    # confirmation is a server-side status refresh.
    payment_ref: str | None = Field(default=None, min_length=1, max_length=200)
    signature: str | None = Field(default=None, min_length=1, max_length=400)


class PaymentRefreshRequest(BaseModel):
    """Ask the backend to re-read the order from the provider. Carries no proof of payment."""

    model_config = ConfigDict(extra="forbid")

    order_ref: str = Field(min_length=1, max_length=200)


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
    # Money captured beyond what the booking was owed (0.00 normally). Refundable through the
    # refund API; it never counts as the booking being paid twice.
    overcollected_amount: Decimal = Decimal("0.00")
    failure_code: str | None = None
    expires_at: datetime | None = None
    captured_at: datetime | None = None
    created_at: datetime
    payment_mode: Literal["PAY_ONLINE", "PAY_AT_SALON"]
    payment_status: str
    collection_method: Literal["CASH", "UPI_DIRECT"] | None = None
    service_amount: Decimal
    online_processing_charge: Decimal
    total_payable: Decimal
    cashfree_order_id: str | None = None
    cashfree_payment_session_id: str | None = None
    provider_payment_reference: str | None = None
    collected_by_owner: bool = False
    collected_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def checkout_provider_aliases(cls, values):
        if isinstance(values, dict):
            values = dict(values)
            manual = values.get("channel") == "manual"
            values.setdefault("payment_mode", "PAY_AT_SALON" if manual else "PAY_ONLINE")
            values.setdefault("payment_status", "COLLECTED_AT_SALON" if manual else {
                "captured":"PAID_ONLINE", "refunded":"REFUNDED", "partially_refunded":"PAID_ONLINE",
                "created":"PAYMENT_PENDING", "authorized":"PAYMENT_PENDING"
            }.get(values.get("status"),"FAILED"))
            values.setdefault("online_processing_charge",Decimal("0"))
            values.setdefault("service_amount",Decimal(values["amount"])-Decimal(values["online_processing_charge"]))
            values.setdefault("total_payable",values["amount"])
            if values.get("provider") == "cashfree":
                values.update(cashfree_order_id=values.get("provider_order_reference"),
                              cashfree_payment_session_id=values.get("provider_session_id"))
        return values


class RefundResponse(BaseModel):
    """One refund."""

    id: str
    payment_id: str
    amount: Decimal
    status: str
    reason: str | None = None
    applies_to_excess: bool = False
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
    commission_reversed: Decimal
    platform_commission_net: Decimal
    overcollected: Decimal
    online_net: Decimal
    manual_recorded: Decimal
    online_payment_count: int
    manual_payment_count: int
    note: str


class SettlementAccountResponse(BaseModel):
    """Salon payee account at the provider (split-settlement model only)."""

    provider_enabled: bool
    supported: bool
    requires_details: bool = False
    # not_started | pending | needs_action | active | rejected | suspended
    onboarding_status: str
    requirements: list[str] = Field(default_factory=list)
    account_reference_masked: str | None = None


class SettlementRegistrationRequest(BaseModel):
    """KYC and payout details for payee registration.

    Used once in memory to call the provider. Never stored, logged, echoed in errors or
    returned. Either (bank_account_number + ifsc) or upi_id is required, not both.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, repr=False)

    legal_name: str = Field(min_length=2, max_length=100)
    contact_email: EmailStr
    contact_phone: str = Field(pattern=r"^[6-9][0-9]{9}$")
    account_type: Literal["individual", "business"]
    business_type: str = Field(min_length=2, max_length=60)
    pan: str = Field(pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    bank_account_number: str | None = Field(default=None, pattern=r"^[0-9]{9,18}$")
    ifsc: str | None = Field(default=None, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")
    upi_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{2,64}@[A-Za-z]{2,32}$")

    @model_validator(mode="after")
    def exactly_one_destination(self) -> "SettlementRegistrationRequest":
        bank = self.bank_account_number is not None or self.ifsc is not None
        if bank and (self.bank_account_number is None or self.ifsc is None):
            raise ValueError("bank_account_number and ifsc must be provided together")
        if bank == (self.upi_id is not None):
            raise ValueError("provide either bank details or a UPI id, not both or neither")
        return self


class WebhookAckResponse(BaseModel):
    """Acknowledgement of a webhook delivery."""

    status: Literal["accepted", "duplicate", "ignored"]
