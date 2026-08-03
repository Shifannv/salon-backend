from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class StaffCreate(APIModel):
    salon_id: str
    name: str
    photo_url: str | None = None
    specialization: str | None = None
    working_hours: dict | None = None
    is_active: bool = True


class StaffOut(StaffCreate):
    id: str


class StaffServiceCreate(APIModel):
    staff_id: str
    service_id: str
    duration_minutes: int | None = Field(default=None, gt=0)
    price_override: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    specialization: str | None = None
    language_codes: list[str] = Field(default_factory=list)
    is_active: bool = True


class StaffServiceOut(StaffServiceCreate):
    id: str


class BlockedSlotCreate(APIModel):
    staff_id: str | None = None
    salon_id: str | None = None
    start_datetime: datetime
    end_datetime: datetime
    block_type: str = "other"
    reason: str | None = None
    is_full_day: bool = False
    is_recurring: bool = False
    recurrence_rule: str | None = None


class BlockedSlotOut(BlockedSlotCreate):
    id: str
