from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.enums import ApprovalMode
from app.schemas.common import APIModel


class SalonCreate(APIModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str = "Asia/Kolkata"
    working_hours: dict = Field(default_factory=dict)
    approval_mode: ApprovalMode = ApprovalMode.manual
    slot_interval_minutes: int = Field(default=15, gt=0)
    profile_completed: bool = True


class SalonUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    timezone: str | None = None
    working_hours: dict | None = None
    approval_mode: ApprovalMode | None = None
    slot_interval_minutes: int | None = Field(default=None, gt=0)
    profile_completed: bool | None = None


class SalonImageCreate(APIModel):
    url: str
    caption: str | None = None
    is_main: bool = False
    sort_order: int = 0


class SalonImageOut(SalonImageCreate):
    id: str
    salon_id: str


class SalonHolidayCreate(APIModel):
    holiday_date: date
    title: str | None = None
    is_recurring: bool = False


class SalonHolidayOut(SalonHolidayCreate):
    id: str
    salon_id: str


class SalonOut(APIModel):
    id: str
    owner_id: str
    name: str
    description: str | None
    category: str | None
    address: str | None
    city: str | None
    lat: float | None
    lng: float | None
    timezone: str
    working_hours: dict
    approval_mode: ApprovalMode
    slot_interval_minutes: int
    qr_token: str
    profile_completed: bool
    is_active: bool
    images: list[SalonImageOut] = Field(default_factory=list)


class SalonListItem(APIModel):
    id: str
    name: str
    address: str | None
    city: str | None
    image_url: str | None = None
    rating: float | None = None
    distance_km: float | None = None
    starting_price: Decimal | None = None


class CategoryCreate(APIModel):
    name: str
    slug: str
    image_url: str | None = None
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True


class SubcategoryCreate(CategoryCreate):
    category_id: str


class CategoryOut(CategoryCreate):
    id: str


class SubcategoryOut(SubcategoryCreate):
    id: str


class ServiceCreate(APIModel):
    salon_id: str
    subcategory_id: str
    name: str
    description: str | None = None
    duration_minutes: int = Field(gt=0)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    is_active: bool = True


class ServiceUpdate(APIModel):
    subcategory_id: str | None = None
    name: str | None = None
    description: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    is_active: bool | None = None


class ServiceOut(ServiceCreate):
    id: str
