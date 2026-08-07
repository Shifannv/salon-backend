"""Admin API request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

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
    name: str
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    timezone: str
    approval_mode: str
    profile_completed: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUpdateSalonRequest(BaseModel):
    """Admin-editable salon fields."""

    name: str | None = Field(default=None, min_length=1)
    timezone: str | None = None


class AdminDeactivateSalonResponse(BaseModel):
    """Response after deactivating a salon."""

    id: str
    owner_id: str


# ── Catalog schemas ───────────────────────────────────────────────────────────

class CategoryCreateRequest(BaseModel):
    """Create service category request."""

    name: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9-]+$")
    image_url: str | None = None
    description: str | None = None
    sort_order: int = 0


class CategoryUpdateRequest(BaseModel):
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


class SubcategoryCreateRequest(BaseModel):
    """Create service subcategory request."""

    category_id: str
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9-]+$")
    image_url: str | None = None
    description: str | None = None
    sort_order: int = 0


class SubcategoryUpdateRequest(BaseModel):
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
