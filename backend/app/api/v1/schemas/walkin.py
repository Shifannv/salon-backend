"""Walk-in specific API schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class WalkInStaffSummary(BaseModel):
    """Staff member summary for walk-in display."""

    id: str
    name: str
    photo_url: str | None = None
    specialization: str | None = None


class WalkInServiceSummary(BaseModel):
    """Service summary for walk-in display."""

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


class WalkInSalonResponse(BaseModel):
    """Walk-in salon page — salon info + services + staff.

    Returned by GET /v1/walkin/{qr_token}.
    The web app uses this as the single data fetch on page load:
    - Mini-header: name, city, address, image_url
    - Service chips: services[]
    - Staff chips: staff[]
    Slot availability is fetched separately via GET /v1/availability.
    """

    id: str
    name: str
    description: str | None = None
    city: str | None = None
    address: str | None = None      # for the mini-header location line
    image_url: str | None = None    # for the optional hero thumbnail
    timezone: str
    approval_mode: str
    services: list[WalkInServiceSummary] = Field(default_factory=list)
    staff: list[WalkInStaffSummary] = Field(default_factory=list)


class WalkInVerifyPhoneRequest(BaseModel):
    """Phone OTP send/verify request.

    Send with phone only to trigger the OTP.
    Send with phone + otp to verify and get a JWT.
    """

    phone: str = Field(description="Phone number including country code, e.g. +919876543210")
    otp: str | None = Field(default=None, description="6-digit OTP received by SMS")


class WalkInVerifyPhoneResponse(BaseModel):
    """OTP send or verify response."""

    verified: bool
    access_token: str | None = None
    refresh_token: str | None = None
