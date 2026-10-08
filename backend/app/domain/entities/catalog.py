"""Service catalog domain entities."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ServiceCategory:
    """Top-level service catalog category (super-admin curated)."""

    id: str
    name: str
    slug: str
    image_url: str | None
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    subcategories: list["ServiceSubcategory"] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ServiceSubcategory:
    """Service subcategory nested under a category."""

    id: str
    category_id: str
    name: str
    slug: str
    image_url: str | None
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Service:
    """A bookable service offered by a salon."""

    id: str
    salon_id: str
    subcategory_id: str
    name: str
    description: str | None
    duration_minutes: int
    price: object  # Decimal — avoid importing to stay pure
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category_name: str | None = None
    subcategory_name: str | None = None
    photo_url: str | None = None
