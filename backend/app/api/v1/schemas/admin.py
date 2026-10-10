from app.api.v1.schemas.media_urls import HostedMediaRequest

"""Admin API request/response schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictInt, field_validator

from app.api.v1.schemas.platform import SalonImageResponse, ServiceResponse, StaffResponse

# ── Admin salon schemas ───────────────────────────────────────────────────────

class AdminCreateSalonRequest(BaseModel):
    """Request to create a salon owner + salon."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)
    salon_name: str = Field(min_length=1)
    timezone: str = Field(default="Asia/Kolkata")


class AdminSalonResponse(BaseModel):
    """Admin view of a salon (includes owner info)."""

    id: str
    owner_id: str
    owner_email: str | None = None
    owner_name: str | None = None
    owner_phone: str | None = None
    owner_avatar_url: str | None = None
    owner_phone_verified: bool | None = None
    owner_is_active: bool | None = None
    name: str
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    working_hours: dict[str, Any] = Field(default_factory=dict)
    slot_interval_minutes: int | None = None
    qr_token: str | None = None
    timezone: str
    approval_mode: str
    profile_completed: bool
    is_active: bool
    # --- admin approval gate (added by migration 0015) ---
    approval_status: Literal["pending", "approved", "rejected"]
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejection_reason: str | None = None
    # --- super-admin discovery ranking (migration 0017); higher ranks first ---
    display_priority: int = 0
    discovery_visibility: Literal["listed", "search_only", "hidden"] = "listed"
    home_placement: Literal["top", "normal", "below", "random"] = "normal"
    created_at: datetime
    updated_at: datetime
    updated_by: str | None = None

    @field_validator("id", "owner_id", "approved_by", "updated_by", mode="before")
    @classmethod
    def stringify_ids(cls, value: object) -> str | None:
        return str(value) if value is not None else None


class AdminApproveSalonRequest(BaseModel):
    """Body for approving a salon (no required fields)."""

    # Reserved for future fields (e.g. an approval note).


class AdminSalonOnboardingResponse(AdminSalonResponse):
    """Full salon submission, accessible only to super admins."""

    images: list[SalonImageResponse] = Field(default_factory=list)
    services: list[ServiceResponse] = Field(default_factory=list)
    staff: list[StaffResponse] = Field(default_factory=list)


class AdminRejectSalonRequest(BaseModel):
    """Body for rejecting a salon."""

    rejection_reason: str = Field(min_length=1, description="Reason shown to the owner")


class AdminUpdateSalonRequest(BaseModel):
    """Admin-editable salon fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    timezone: str | None = None
    display_priority: StrictInt | None = Field(default=None, ge=0, le=100000)
    discovery_visibility: Literal["listed", "search_only", "hidden"] | None = None
    home_placement: Literal["top", "normal", "below", "random"] | None = None


class AdminDeactivateSalonResponse(BaseModel):
    """Response after deactivating a salon."""

    id: str
    owner_id: str


# ── Catalog schemas ───────────────────────────────────────────────────────────

class CategoryCreateRequest(HostedMediaRequest):
    """Create service category request."""

    name: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9-]+$")
    image_url: str | None = None
    description: str | None = None
    sort_order: int = 0


class CategoryUpdateRequest(HostedMediaRequest):
    """Update service category request."""

    name: str | None = Field(default=None, min_length=1)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9-]+$")
    image_url: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    """Service category response."""

    id: str
    name: str
    slug: str
    image_url: str | None = None
    description: str | None = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SubcategoryCreateRequest(HostedMediaRequest):
    """Create service subcategory request."""

    category_id: str
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9-]+$")
    image_url: str | None = None
    description: str | None = None
    sort_order: int = 0


class SubcategoryUpdateRequest(HostedMediaRequest):
    """Update service subcategory request."""

    name: str | None = Field(default=None, min_length=1)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9-]+$")
    image_url: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class SubcategoryResponse(BaseModel):
    """Service subcategory response."""

    id: str
    category_id: str
    name: str
    slug: str
    image_url: str | None = None
    description: str | None = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LanguageResponse(BaseModel):
    """Language reference response."""

    code: str
    name: str
