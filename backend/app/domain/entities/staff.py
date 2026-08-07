"""Staff domain entities."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Language:
    """A spoken language a staff member supports."""

    code: str   # ISO 639-1
    name: str


@dataclass(frozen=True, slots=True)
class StaffService:
    """A service offered by a staff member with optional overrides."""

    id: str
    staff_id: str
    service_id: str
    duration_minutes: int | None   # None → use service default
    price_override: object | None  # Decimal | None
    specialization: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    languages: list[Language] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BlockedSlot:
    """A period when a staff member or whole salon is unavailable."""

    id: str
    staff_id: str | None   # None → salon-wide block
    salon_id: str | None
    start_datetime: datetime
    end_datetime: datetime
    block_type: str         # 'leave' | 'break' | 'lunch' | 'training' | 'holiday' | 'other'
    reason: str | None
    is_full_day: bool
    is_recurring: bool
    recurrence_rule: str | None
    recurrence_end: object | None  # date | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Staff:
    """A barber or stylist employed by a salon."""

    id: str
    salon_id: str
    profile_id: str | None  # None in Phase 1 — staff have no login yet
    name: str
    photo_url: str | None
    specialization: str | None
    working_hours: dict | None  # None → inherit salon hours
    is_active: bool
    created_at: datetime
    updated_at: datetime
    services: list[StaffService] = field(default_factory=list)
