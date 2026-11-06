"""Booking, availability and cancellation API schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.api.v1.schemas.common import UuidParam
from app.domain.entities.payment import derive_payment_state


class AvailabilityResponse(BaseModel):
    """Available slot response.

    Frontend ``TimeSlotPicker`` expects:
      - ``id``         — stable key for the slot (formatted start time, e.g. "09:00 AM")
      - ``time``       — human-readable label shown in the UI (same value as ``id``)
      - ``barberName`` — optional barber context displayed beside the time chip

    We also keep ``slot_start`` / ``slot_end`` for any consumer that needs the
    raw datetimes.
    """

    slot_start: datetime
    slot_end: datetime
    # ── Frontend TimeSlotPicker fields ────────────────────────────────────────
    id: str  # e.g. "09:00 AM" — stable key and display label
    time: str  # same as id; explicit field for clarity
    barberName: str | None = None  # camelCase to match the TS type verbatim


class VisitSegmentRequest(BaseModel):
    """An ordered group of services performed by one professional."""

    staff_id: UuidParam
    service_ids: list[UuidParam] = Field(min_length=1, max_length=30)


class VisitAvailabilityRequest(BaseModel):
    salon_id: UuidParam
    date: date
    segments: list[VisitSegmentRequest] = Field(min_length=1, max_length=30)


class BookingCreateRequest(BaseModel):
    """Create booking request."""

    salon_id: UuidParam
    staff_id: UuidParam
    service_ids: list[UuidParam] = Field(min_length=1, max_length=30)
    segments: list[VisitSegmentRequest] | None = Field(default=None, min_length=1, max_length=30)
    start_datetime: AwareDatetime
    customer_name: str = Field(max_length=200)
    customer_phone: str | None = Field(default=None, max_length=32)
    source: Literal["app", "manual_walkin", "qr_walkin"] = "app"
    notes: str | None = Field(default=None, max_length=1000)
    payment_preference: Literal["pay_at_salon", "pay_advance", "pay_full"] | None = None


class BookingSegmentResponse(BaseModel):
    staff_name: str | None = None
    ordinal: int
    staff_id: str
    service_ids: list[str]
    slot_start: datetime
    slot_end: datetime
    price: Decimal
    duration_minutes: int


class VisitAvailabilityResponse(AvailabilityResponse):
    segments: list[BookingSegmentResponse]
    total_price: Decimal


class BookingLineResponse(BaseModel):
    """Booking service line response."""

    service_id: str
    service_name: str
    duration_minutes: int
    price: Decimal


# Statuses that allow a customer (or salon) to cancel.
_CANCELLABLE_STATUSES = frozenset({"pending", "confirmed"})


class BookingResponse(BaseModel):
    """Booking response."""

    change_version: int = 0
    committed_reschedules: int = 0
    service_fulfilment_amount: Decimal | None = None
    checkout_policy_version: str = "customer_processing_v1"

    id: str
    salon_id: str
    staff_id: str
    customer_id: str | None = None
    customer_name: str
    customer_phone: str | None = None
    phone_verified: bool
    source: str
    status: str
    start_datetime: datetime
    end_datetime: datetime
    estimated_end_datetime: datetime | None = None
    total_duration_minutes: int
    total_price: Decimal
    payment_status: str
    payment_method: str | None = None
    payment_preference: str | None = None
    # Money columns are a derived cache of the payment ledger (see PAYMENTS.md).
    currency: str = "INR"
    deposit_amount: Decimal | None = None
    paid_amount: Decimal = Decimal("0")
    refunded_amount: Decimal = Decimal("0")
    payment_state: str = "unpaid"
    payment_mode: str = "PAY_AT_SALON"
    checkout_payment_status: str = "PAY_AT_SALON_PENDING"
    service_amount: Decimal = Decimal("0")
    online_processing_charge: Decimal = Decimal("0")
    total_payable: Decimal = Decimal("0")
    pending_amount_to_collect: Decimal = Decimal("0")
    collection_instructions: str | None = None
    rejection_reason: str | None = None
    cancellation_reason: str | None = None
    notes: str | None = None
    services: list[BookingLineResponse] = Field(default_factory=list)
    segments: list[BookingSegmentResponse] = Field(default_factory=list)
    is_multi_staff: bool = False
    # ── Denormalized display fields (joined from salons + staff) ──────────
    salon_name: str | None = None
    salon_address: str | None = None
    salon_image: str | None = None
    staff_name: str | None = None
    staff_photo_url: str | None = None
    created_at: datetime
    updated_at: datetime
    # ── Computed UI helper ────────────────────────────────────────────────
    latest_payment_request_status: str | None = None
    latest_payment_request_decision: str | None = None
    latest_payment_request_reason: str | None = None
    latest_cancellation_request_status: str | None = None
    latest_cancellation_request_decision: str | None = None
    latest_cancellation_request_reason: str | None = None
    can_cancel: bool = False
    can_request_cancellation: bool = False
    can_confirm_payment: bool = False
    can_record_payment: bool = False

    @model_validator(mode="after")
    def _set_can_cancel(self) -> "BookingResponse":
        """Derive customer actions from the configured server policy."""

        now = datetime.now(tz=self.start_datetime.tzinfo)
        active = self.status in _CANCELLABLE_STATUSES
        self.can_cancel = active and now < self.start_datetime
        self.can_request_cancellation = False
        self.payment_state = derive_payment_state(
            self.payment_status, self.paid_amount, self.refunded_amount
        ).value
        self.service_amount = self.total_price
        self.payment_mode = "PAY_AT_SALON" if self.payment_preference in {None, "pay_at_salon"} else "PAY_ONLINE"
        if self.payment_mode == "PAY_AT_SALON":
            self.online_processing_charge = Decimal("0")
            self.total_payable = self.total_price
            self.pending_amount_to_collect = max(Decimal("0"), self.total_price - self.paid_amount + self.refunded_amount)
            self.checkout_payment_status = "COLLECTED_AT_SALON" if self.payment_status == "paid" else "PAY_AT_SALON_PENDING"
            self.collection_instructions = "Collect cash or direct UPI from customer before completing service."
        else:
            self.total_payable = self.total_price + self.online_processing_charge
            self.checkout_payment_status = "PAID_ONLINE" if self.payment_status == "paid" else "UNPAID"
        self.can_confirm_payment = (
            self.status in {"confirmed", "completed"}
            and self.payment_status == "unpaid"
            and self.payment_preference == "pay_at_salon"
            and now >= self.start_datetime
            and self.latest_payment_request_status != "pending"
        )
        return self


class CancellationQuoteResponse(BaseModel):
    booking_id: UuidParam
    can_cancel: bool
    payment_preference: str | None
    paid_online: bool
    currency: str
    amount_paid: Decimal
    already_refunded: Decimal
    refund_amount: Decimal | None
    deduction_amount: Decimal | None
    message: str
    requires_review: bool


class DelayBookingRequest(BaseModel):
    """Owner/staff request to record a delayed completion estimate."""

    estimated_end_datetime: datetime
    notify_affected_customers: bool = True

    @field_validator("estimated_end_datetime")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject ambiguous local timestamps."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("estimated_end_datetime must include a timezone offset")
        return value


class RejectBookingRequest(BaseModel):
    """Reject booking request.

    The barber must pick a reason so the customer knows why their booking
    was declined.  Free-form text is the backing field; the UI is expected
    to offer preset chips that map to localised strings.
    """

    rejection_reason: str = Field(
        min_length=1,
        max_length=500,
        description="Human-readable reason shown to the customer in the push notification and booking detail screen.",
    )


# ── Cancellation reason codes ─────────────────────────────────────────────────
# Customer-side codes — shown in the customer app cancellation flow UI.
CustomerCancellationReasonCode = Literal[
    "schedule_conflict",
    "found_better",
    "personal_emergency",
    "booked_by_mistake",
    "service_not_needed",
    "other",
]

# Barber/owner-side codes — shown in the owner app when cancelling on behalf
# of the salon.  These are intentionally different from customer codes.
BarberCancellationReasonCode = Literal[
    "barber_unavailable",
    "salon_emergency",
    "overbooking",
    "customer_no_show",
    "equipment_issue",
    "other",
]

# Union kept for schema docs / OpenAPI — both sets share the same DB column.
CancellationReasonCode = CustomerCancellationReasonCode | BarberCancellationReasonCode


class CancelBookingRequest(BaseModel):
    """Optional body for the customer cancel-booking endpoint.

    Both fields are optional so customers who cancel without specifying a
    reason (e.g. one-tap cancel) continue to work unchanged.
    """

    reason_code: CustomerCancellationReasonCode | None = Field(
        default=None,
        description="Structured reason chip from the customer cancellation flow UI.",
    )
    reason_text: str | None = Field(
        default=None,
        max_length=500,
        description="Free-text note typed by the customer (may be empty).",
    )


class BarberCancelBookingRequest(BaseModel):
    """Request body for the barber/owner cancel-booking endpoint.

    ``reason_code`` is **required** when the salon cancels so the customer
    always receives a clear, localised explanation.  ``reason_text`` is
    optional additional context.

    The combined human-readable string (e.g. ``"Barber unavailable — staffing
    issue this week"``) is stored in ``bookings.cancellation_reason`` and sent
    to the customer as a push notification body.
    """

    reason_code: BarberCancellationReasonCode = Field(
        description="Structured reason chip shown to the customer.",
    )
    reason_text: str | None = Field(
        default=None,
        max_length=500,
        description="Optional free-text note with additional context (shown to the customer).",
    )


class NoShowBookingRequest(BaseModel):
    """Explicit salon attendance decision; the server enforces the grace period."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class PaymentRequest(BaseModel):
    """Record booking payment request."""

    payment_method: Literal["cash", "upi_direct"]
