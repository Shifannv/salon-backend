"""Salon, holiday, blocked-slot, image upload, payout and setup API schemas."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)

from app.api.v1.schemas.common import IdStr, UuidAsStr, UuidParam
from app.api.v1.schemas.media_urls import HostedMediaRequest
from app.application.salon_photos import visible_salon_photos
from app.core.config import settings
from app.domain.services.checkout import online_checkout_available


class CustomerAvailabilityResponse(BaseModel):
    """Backend-owned booking and payment capability, computed on every response (never cached).

    ``payment_options`` lists only the methods this salon can be booked with right now: empty while the salon
    is not accepting bookings, ``PAY_AT_SALON`` otherwise, plus ``PAY_ONLINE`` only when the platform's online
    payment gateway is enabled. A customer-specific block (``pay_at_salon_temporarily_blocked`` and similar)
    is not salon-level, so it is reported as a 409 error code when booking, not here.
    """

    accepts_bookings: bool = Field(default=True, description="False while the salon is paused or not bookable.")
    payment_options: list[Literal["PAY_AT_SALON", "PAY_ONLINE"]] = Field(
        default_factory=lambda: ["PAY_AT_SALON"],
        description="Payment methods currently permitted for a new booking at this salon.",
    )
    online_payment_available: bool = Field(default=False, description="True only when PAY_ONLINE is listed.")
    online_payment_unavailable_reason: str | None = Field(
        default="Online payment coming soon.",
        description="Customer-facing reason online payment is not offered; null when it is available.",
    )

    @model_validator(mode="after")
    def customer_availability(self) -> "CustomerAvailabilityResponse":
        from app.infrastructure.payments.resolver import get_payment_resolver
        self.accepts_bookings = bool(getattr(self, "accepting_bookings", True))
        self.online_payment_available = self.accepts_bookings and online_checkout_available(
            get_payment_resolver().enabled, settings.booking_checkout_policy_version,
        )
        self.payment_options = (["PAY_AT_SALON"] if self.accepts_bookings else [])
        if self.online_payment_available:
            self.payment_options.append("PAY_ONLINE")
        self.online_payment_unavailable_reason = (
            None if self.online_payment_available else "Online payment coming soon."
        )
        return self


class SalonSummaryResponse(CustomerAvailabilityResponse):
    """Salon list response item.

    Services are NOT embedded here. Call GET /salons/{salon_id}/services
    to fetch services for a specific salon.
    """

    id: str
    name: str
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str
    approval_mode: str
    accepting_bookings: bool = True
    profile_completed: bool
    is_active: bool
    working_hours: dict[str, Any] | None = None
    image_url: str | None = None
    starting_price: Decimal | None = None
    distance_km: float | None = None
    is_promoted: bool = Field(
        default=False,
        description=(
            "True when the salon is listed higher because of a paid plan or an admin placement. "
            "Customer apps must label these listings as Featured."
        ),
    )


class SalonImageResponse(BaseModel):
    """Salon image response."""

    id: UuidAsStr
    salon_id: UuidAsStr
    url: str
    caption: str | None = None
    is_main: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


def _visible_photos(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    return visible_salon_photos([image.model_dump() if isinstance(image, BaseModel) else image for image in value])


SalonPhotos = Annotated[
    list[SalonImageResponse], BeforeValidator(_visible_photos),
    Field(max_length=3, description="One separate cover (is_main=true) and at most two distinct gallery slides."),
]


class ServiceResponse(BaseModel):
    """Service response."""

    id: str
    salon_id: str
    subcategory_id: str
    menu_category_id: str | None = None
    selection_group: str | None = "__category__"
    name: str
    duration_minutes: int
    price: Decimal
    is_active: bool
    category_name: str | None = None
    subcategory_name: str | None = None
    photo_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SalonDetailResponse(CustomerAvailabilityResponse):
    """Salon detail response.

    Images are embedded here as they are always needed for the detail view.
    Services and staff are NOT embedded — use the dedicated endpoints:
      - GET /salons/{salon_id}/services
      - GET /salons/{salon_id}/staff
    """

    id: str
    name: str
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str
    working_hours: dict[str, Any]
    approval_mode: str
    accepting_bookings: bool = True
    profile_completed: bool
    is_active: bool
    images: SalonPhotos = Field(default_factory=list)


class OwnerSalonResponse(BaseModel):
    """Owner salon response."""

    id: str
    owner_id: str
    name: str
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str
    working_hours: dict[str, Any]
    approval_mode: str
    accepting_bookings: bool
    slot_interval_minutes: int
    qr_token: str
    profile_completed: bool
    approval_status: Literal["pending", "approved", "rejected"]
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejection_reason: str | None = None
    is_active: bool
    images: SalonPhotos = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OwnerSalonUpdateRequest(BaseModel):
    """Owner salon update request."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str | None = None
    working_hours: dict[str, Any] | None = None
    approval_mode: Literal["auto", "manual"] | None = None


    @field_validator("name", "address", "city")
    @classmethod
    def required_details_cannot_be_cleared(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("This business detail cannot be empty")
        return value.strip()


class OwnerSalonCompleteProfileRequest(OwnerSalonUpdateRequest):
    """Final onboarding payload used to submit an owner salon for admin review."""


class QrCodeUrlResponse(BaseModel):
    """Public image URL that can be displayed without an Authorization header."""

    url: str
    cached: bool = False


class OwnerSalonSettingsRequest(BaseModel):
    """Owner salon settings request."""

    approval_mode: Literal["auto", "manual"] | None = None
    working_hours: dict[str, Any] | None = None
    accepting_bookings: StrictBool | None = None


class SalonImageCreateRequest(HostedMediaRequest):
    """Create salon image request."""

    url: str
    caption: str | None = None
    is_main: bool = False
    sort_order: int = 0


class SalonImageUpdateRequest(HostedMediaRequest):
    """Update salon image request."""

    url: str | None = None
    caption: str | None = None
    is_main: bool | None = None
    sort_order: int | None = None


class HolidayCreateRequest(BaseModel):
    """Create salon holiday request."""

    holiday_date: date
    title: str | None = Field(default=None, max_length=200)
    is_recurring: bool = False


class HolidayResponse(BaseModel):
    """Salon holiday response."""

    id: IdStr
    salon_id: IdStr
    holiday_date: date
    title: str | None = None
    is_recurring: bool
    created_at: datetime
    updated_at: datetime


class BlockedSlotCreateRequest(BaseModel):
    """Create a blocked slot (staff-scoped or salon-wide)."""

    staff_id: UuidParam | None = Field(
        default=None,
        description="Staff member to block. Leave null for a salon-wide block.",
    )
    start_datetime: AwareDatetime
    end_datetime: AwareDatetime
    block_type: Literal["leave", "break", "lunch", "training", "holiday", "other"] = "other"
    reason: str | None = None
    is_full_day: bool = False
    is_recurring: bool = False
    recurrence_rule: str | None = Field(
        default=None, description="iCal RRULE string. Stored but not yet interpreted."
    )
    recurrence_end: date | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> "BlockedSlotCreateRequest":
        if self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime must be later than start_datetime")
        return self


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
    """Request body for generating a short-lived backend upload capability.

    The client PUTs image bytes to the backend validation gateway using the returned URL.
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
    result_url: str | None = Field(default=None, description="Read-only URL (cannot upload). GET it after PUT for WebP variant URLs and metadata.")
    public_url: str = Field(description="Permanent public URL of the uploaded object. Store this in the DB.")
    expires_in: int = Field(description="Upload URL TTL in seconds.")


_UPI_RE = re.compile(r"^[A-Za-z0-9._-]{2,255}@[A-Za-z]{2,64}$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_ACCOUNT_RE = re.compile(r"^[0-9]{9,18}$")


def _blank_to_none(value: Any) -> Any:
    """Strip strings; a blank string is treated like an explicit null (clear)."""

    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class OwnerPayoutAccountRequest(BaseModel):
    """Partial update of the owner's payout destination (merge semantics).

    Omitted fields keep their stored value; an explicit ``null`` clears the field.
    Error messages never include the submitted value.
    """

    model_config = ConfigDict(extra="forbid")

    account_holder_name: str | None = None
    upi_id: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    ifsc: str | None = None

    @field_validator("account_holder_name", mode="after")
    @classmethod
    def _holder(cls, value: str | None) -> str | None:
        value = _blank_to_none(value)
        if value is not None and not 2 <= len(value) <= 100:
            raise ValueError("Account holder name must be 2-100 characters")
        return value

    @field_validator("upi_id", mode="after")
    @classmethod
    def _upi(cls, value: str | None) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        if not _UPI_RE.fullmatch(value):
            raise ValueError("Enter a valid UPI ID such as name@bank")
        return value.lower()

    @field_validator("bank_name", mode="after")
    @classmethod
    def _bank(cls, value: str | None) -> str | None:
        value = _blank_to_none(value)
        if value is not None and len(value) > 100:
            raise ValueError("Bank name must be at most 100 characters")
        return value

    @field_validator("bank_account_number", mode="after")
    @classmethod
    def _account(cls, value: str | None) -> str | None:
        value = _blank_to_none(value)
        if value is not None and not _ACCOUNT_RE.fullmatch(value):
            raise ValueError("Account number must be 9-18 digits")
        return value

    @field_validator("ifsc", mode="after")
    @classmethod
    def _ifsc(cls, value: str | None) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        value = value.upper()
        if not _IFSC_RE.fullmatch(value):
            raise ValueError("Enter a valid 11-character IFSC code")
        return value


class OwnerPayoutAccountResponse(BaseModel):
    """Masked payout account. The full account number is never returned."""

    configured: bool
    account_holder_name: str | None = None
    upi_id: str | None = None
    bank_name: str | None = None
    bank_account_last4: str | None = None
    ifsc: str | None = None
    has_upi: bool
    has_bank: bool
    updated_at: datetime | None = None


class PayoutSnapshotResponse(BaseModel):
    """Point-in-time payout destination; the account number is last four digits only."""

    account_holder_name: str | None = None
    upi_id: str | None = None
    bank_name: str | None = None
    ifsc: str | None = None
    bank_account_last4: str | None = None


class PayoutHistoryEntryResponse(BaseModel):
    """One change to the payout destination."""

    id: str
    changed_at: datetime
    action: Literal["created", "updated"]
    changed_fields: list[str] = Field(default_factory=list)
    changed_by_name: str | None = None
    before: PayoutSnapshotResponse | None = None
    after: PayoutSnapshotResponse


class SetupItemResponse(BaseModel):
    """One step of the new-owner setup checklist."""

    key: Literal["profile_basics", "working_hours", "photos", "services", "staff", "payout"]
    title: str
    description: str
    done: bool
    action: Literal["business_profile", "working_hours", "photos", "services", "staff", "payout"]


class OwnerSetupStatusResponse(BaseModel):
    """Authoritative checklist of what a new owner still has to finish."""

    completed_count: int
    total_count: int
    is_complete: bool
    items: list[SetupItemResponse]
