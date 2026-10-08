"""Salon domain entities."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WorkingHours:
    """One day's open/close window."""

    open: str   # "HH:MM"
    close: str  # "HH:MM"


@dataclass(frozen=True, slots=True)
class SalonImage:
    """A single salon photo."""

    id: str
    salon_id: str
    url: str
    caption: str | None
    is_main: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SalonHoliday:
    """A day the salon is closed."""

    id: str
    salon_id: str
    holiday_date: object  # datetime.date — avoid importing to stay pure
    title: str | None
    is_recurring: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Salon:
    """Core salon aggregate."""

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
    working_hours: dict  # keyed by day abbreviation
    approval_mode: str   # 'auto' | 'manual'
    slot_interval_minutes: int
    qr_token: str
    profile_completed: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[SalonImage] = field(default_factory=list)
    holidays: list[SalonHoliday] = field(default_factory=list)
    approval_status: str = "pending"
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejection_reason: str | None = None
