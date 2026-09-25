"""Frontend-facing API schemas."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import settings


class ProfileUpdateRequest(BaseModel):
    """Shared profile update request (PATCH /profiles/me).

    Used by owners, staff, and customers — not customer-only despite the name.
    Fields are all optional; only explicitly sent fields are written.
    Sending ``null`` for a nullable field (e.g. ``phone``) clears it.
    """

    full_name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    avatar_url: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, value: str | None) -> str | None:
        """Normalize and reject obvious fake customer phone numbers."""

        if value is None:
            return None

        raw = value.strip()
        if raw.startswith("+91"):
            digits = raw[3:]
        else:
            digits = raw

        sequential_runs = {
            "012345", "12345", "23456", "34567", "45678", "56789",
            "98765", "87654", "76543", "65432", "54321", "43210",
        }
        if (
            not digits.isdigit()
            or len(digits) != 10
            or digits[0] not in "6789"
            or len(set(digits)) == 1
            or digits[:2] * 5 == digits
            or any(sequence in digits for sequence in sequential_runs)
        ):
            raise ValueError("Enter a valid 10-digit Indian mobile number")

        return f"+91{digits}"


class ProfileResponse(BaseModel):
    """Profile response."""

    id: str
    role: str
    full_name: str | None
    email: str | None
    phone: str | None
    phone_verified: bool
    avatar_url: str | None
    is_active: bool


class SalonSummaryResponse(BaseModel):
    """Salon list response item.

    Services are NOT embedded here. Call GET /salons/{salon_id}/services
    to fetch services for a specific salon.
    """

    id: str
    name: str
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str
    approval_mode: str
    profile_completed: bool
    is_active: bool
    working_hours: dict[str, Any] | None = None
    image_url: str | None = None
    starting_price: Decimal | None = None
    distance_km: float | None = None


class SalonImageResponse(BaseModel):
    """Salon image response."""

    id: str
    salon_id: str
    url: str
    caption: str | None = None
    is_main: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ServiceResponse(BaseModel):
    """Service response."""

    id: str
    salon_id: str
    subcategory_id: str
    name: str
    description: str | None = None
    duration_minutes: int
    price: Decimal
    is_active: bool
    category_name: str | None = None
    subcategory_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SalonDetailResponse(BaseModel):
    """Salon detail response.

    Images are embedded here as they are always needed for the detail view.
    Services and staff are NOT embedded — use the dedicated endpoints:
      - GET /salons/{salon_id}/services
      - GET /salons/{salon_id}/staff
    """

    id: str
    name: str
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str
    working_hours: dict[str, Any]
    approval_mode: str
    profile_completed: bool
    is_active: bool
    images: list[SalonImageResponse] = Field(default_factory=list)


class OwnerSalonResponse(BaseModel):
    """Owner salon response."""

    id: str
    owner_id: str
    name: str
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str
    working_hours: dict[str, Any]
    approval_mode: str
    slot_interval_minutes: int
    qr_token: str
    profile_completed: bool
    is_active: bool
    images: list[SalonImageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OwnerSalonUpdateRequest(BaseModel):
    """Owner salon update request."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str | None = None
    working_hours: dict[str, Any] | None = None
    approval_mode: Literal["auto", "manual"] | None = None


class OwnerSalonCompleteProfileRequest(OwnerSalonUpdateRequest):
    """Final onboarding payload used to create/update and publish an owner salon."""


class OwnerSalonSettingsRequest(BaseModel):
    """Owner salon settings request."""

    approval_mode: Literal["auto", "manual"] | None = None
    working_hours: dict[str, Any] | None = None


class SalonImageCreateRequest(BaseModel):
    """Create salon image request."""

    url: str
    caption: str | None = None
    is_main: bool = False
    sort_order: int = 0


class SalonImageUpdateRequest(BaseModel):
    """Update salon image request."""

    url: str | None = None
    caption: str | None = None
    is_main: bool | None = None
    sort_order: int | None = None


class HolidayCreateRequest(BaseModel):
    """Create salon holiday request."""

    holiday_date: date
    title: str | None = None
    is_recurring: bool = False


class HolidayResponse(BaseModel):
    """Salon holiday response."""

    id: str
    salon_id: str
    holiday_date: date
    title: str | None = None
    is_recurring: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "salon_id", mode="before")
    @classmethod
    def _coerce_uuid_to_str(cls, v: Any) -> Any:
        """DB returns UUID objects; coerce to str for Pydantic."""
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class ServiceCreateRequest(BaseModel):
    """Create service request."""

    subcategory_id: str | None = None
    name: str
    description: str | None = None
    duration_minutes: int = Field(gt=0)
    price: Decimal = Field(ge=0)
    is_active: bool = True


class ServiceUpdateRequest(BaseModel):
    """Update service request."""

    subcategory_id: str | None = None
    name: str | None = None
    description: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class StaffCreateRequest(BaseModel):
    """Create staff request."""

    profile_id: str | None = None
    name: str
    photo_url: str | None = None
    specialization: str | None = None
    experience: str | None = None
    working_hours: dict[str, Any] | None = None


class StaffUpdateRequest(BaseModel):
    """Update staff request."""

    profile_id: str | None = None
    name: str | None = None
    photo_url: str | None = None
    specialization: str | None = None
    experience: str | None = None
    working_hours: dict[str, Any] | None = None
    is_active: bool | None = None


class StaffResponse(BaseModel):
    """Staff response (owner-facing, includes full detail)."""

    id: str
    salon_id: str
    profile_id: str | None = None
    name: str
    photo_url: str | None = None
    specialization: str | None = None
    experience: str | None = None
    working_hours: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PublicStaffResponse(BaseModel):
    """Customer-facing staff/barber summary for salon detail and booking flow."""

    id: str
    name: str
    photo_url: str | None = None
    specialization: str | None = None


class StaffServiceAssignRequest(BaseModel):
    """Assign service to staff request."""

    service_id: str
    duration_minutes: int | None = Field(default=None, gt=0)
    price_override: Decimal | None = Field(default=None, ge=0)
    specialization: str | None = None


class StaffServiceResponse(BaseModel):
    """Staff service response."""

    id: str
    staff_id: str
    service_id: str
    duration_minutes: int | None = None
    price_override: Decimal | None = None
    specialization: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


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


class BookingCreateRequest(BaseModel):
    """Create booking request."""

    salon_id: str
    staff_id: str
    service_ids: list[str] = Field(min_length=1)
    start_datetime: datetime
    customer_name: str
    customer_phone: str | None = None
    source: Literal["app", "manual_walkin", "qr_walkin"] = "app"
    notes: str | None = None
    payment_preference: Literal["pay_at_salon"] | None = None


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
    rejection_reason: str | None = None
    cancellation_reason: str | None = None
    notes: str | None = None
    services: list[BookingLineResponse] = Field(default_factory=list)
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

    @model_validator(mode="after")
    def _set_can_cancel(self) -> "BookingResponse":
        """Derive customer actions from the configured server policy."""

        now = datetime.now(tz=self.start_datetime.tzinfo)
        active = self.status in _CANCELLABLE_STATUSES
        cutoff = self.start_datetime - timedelta(
            minutes=settings.customer_cancellation_cutoff_minutes
        )
        self.can_cancel = active and now < cutoff
        self.can_request_cancellation = (
            settings.allow_late_cancellation_requests
            and active
            and cutoff <= now < self.end_datetime
            and self.latest_cancellation_request_status != "pending"
        )
        self.can_confirm_payment = (
            self.status in {"confirmed", "completed"}
            and self.payment_status == "unpaid"
            and self.payment_preference == "pay_at_salon"
            and now >= self.start_datetime
            and self.latest_payment_request_status != "pending"
        )
        return self


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


class PaymentRequest(BaseModel):
    """Record booking payment request."""

    payment_method: Literal["cash", "online"]


class NotificationResponse(BaseModel):
    """Notification response."""

    id: str
    user_id: str
    booking_id: str | None = None
    type: str | None = None
    title: str
    body: str | None = None
    read: bool
    read_at: datetime | None = None  # set when read flips true (migration 0002)
    created_at: datetime

    @field_validator("id", "user_id", "booking_id", mode="before")
    @classmethod
    def _coerce_uuid_to_str(cls, v: Any) -> Any:
        """DB returns UUID objects; coerce to str for Pydantic."""
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class MarkAllNotificationsReadResponse(BaseModel):
    """Number of unread notifications marked as read."""

    updated_count: int = Field(ge=0)


class DeviceRegisterRequest(BaseModel):
    """Device registration request."""

    token: str
    platform: str | None = None
    device_name: str | None = None


class DeviceRegisterResponse(BaseModel):
    """Device registration response."""

    id: str
    token: str
    platform: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_uuid_to_str(cls, v: Any) -> Any:
        """DB returns UUID objects; coerce to str for Pydantic."""
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


# ── Phase 3 additions ─────────────────────────────────────────────────────────


class LanguageResponse(BaseModel):
    """Language reference data response."""

    code: str
    name: str


class StaffServiceLanguagesRequest(BaseModel):
    """Set language codes for a staff service assignment (idempotent PUT)."""

    language_codes: list[str] = Field(
        description="ISO 639-1 codes, e.g. ['en', 'ml']. Replaces the current list."
    )


class BlockedSlotCreateRequest(BaseModel):
    """Create a blocked slot (staff-scoped or salon-wide)."""

    staff_id: str | None = Field(
        default=None,
        description="Staff member to block. Leave null for a salon-wide block.",
    )
    start_datetime: datetime
    end_datetime: datetime
    block_type: Literal["leave", "break", "lunch", "training", "holiday", "other"] = "other"
    reason: str | None = None
    is_full_day: bool = False
    is_recurring: bool = False
    recurrence_rule: str | None = Field(
        default=None, description="iCal RRULE string. Stored but not yet interpreted."
    )
    recurrence_end: date | None = None


class BlockedSlotResponse(BaseModel):
    """Blocked slot response."""

    id: str
    staff_id: str | None = None
    salon_id: str | None = None
    start_datetime: datetime
    end_datetime: datetime
    block_type: str
    reason: str | None = None
    is_full_day: bool
    is_recurring: bool
    recurrence_rule: str | None = None
    recurrence_end: date | None = None
    created_at: datetime
    updated_at: datetime



# ── Image upload ───────────────────────────────────────────────────────────────


class ImageUploadUrlRequest(BaseModel):
    """Request body for generating a short-lived R2 upload URL.

    The client PUTs the image directly to Cloudflare R2 using the returned URL.
    """

    content_type: str = Field(
        default="image/jpeg",
        description="MIME type of the image to upload (e.g. 'image/jpeg', 'image/png').",
    )
    filename: str = Field(
        min_length=1,
        description="Original filename (e.g. 'cover.jpg'). Used only to derive the file extension.",
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        """Reject MIME types that are not supported image formats."""
        from app.application.ports.storage_gateway import _ALLOWED_CONTENT_TYPES

        if value not in _ALLOWED_CONTENT_TYPES:
            allowed = ", ".join(sorted(_ALLOWED_CONTENT_TYPES))
            raise ValueError(
                f"Unsupported content_type '{value}'. Allowed types: {allowed}"
            )
        return value


class ImageUploadUrlResponse(BaseModel):
    """Response containing the signed upload URL and resulting public URL.

    Upload flow:
    1. POST /v1/salons/me/images/upload-url  → receive upload_url + public_url
    2. PUT <upload_url> with the image binary and a 'Content-Type: <mime>' header
    3. POST /v1/salons/me/images { "url": "<public_url>", ... } to record in DB
    """

    upload_url: str = Field(description="Signed PUT URL. Client must PUT to this within expires_in seconds.")
    public_url: str = Field(description="Permanent public URL of the uploaded object. Store this in the DB.")
    expires_in: int = Field(description="Upload URL TTL in seconds.")

