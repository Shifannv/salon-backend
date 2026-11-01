"""Trial configuration and current usage for one salon."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.api.v1.schemas.common import IdStr
from app.domain.services.trial_limits import (
    DEFAULT_TRIAL_DAYS,
    MAX_TRIAL_BOOKINGS,
    MAX_TRIAL_DAYS,
)


class TrialLimitsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_days: StrictInt = Field(default=DEFAULT_TRIAL_DAYS, ge=1, le=MAX_TRIAL_DAYS)
    # Required, no default: the super admin sets it for every salon.
    trial_booking_limit: StrictInt = Field(ge=1, le=MAX_TRIAL_BOOKINGS)


class SalonTrialResponse(BaseModel):
    salon_id: IdStr
    trial_days: int
    trial_booking_limit: int | None = None
    trial_started_at: datetime | None = None
    trial_ends_at: datetime | None = None
    bookings_counted: int = 0
    trial_limit_reached_at: datetime | None = None
    state: Literal["not_started", "active", "expired", "quota_reached"]


class TrialUpdateRequest(TrialLimitsRequest):
    """Both fields are required so a partial edit cannot silently reset the other."""

    trial_days: StrictInt = Field(ge=1, le=MAX_TRIAL_DAYS)
    trial_booking_limit: StrictInt = Field(ge=1, le=MAX_TRIAL_BOOKINGS)
