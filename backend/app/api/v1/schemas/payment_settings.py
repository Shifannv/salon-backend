"""Super-admin payment settings API schemas. Percentages are decimals, money is integer paise."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

CommissionBase = Literal["online_amount", "booking_total"]
RateSource = Literal["salon", "platform", "environment"]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentSettingsUpdate(_Request):
    """Rate and base are set together, or both cleared with an explicit null. Neither may be left out."""

    commission_rate_percent: Decimal | None = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    commission_base: CommissionBase | None
    min_payout_paise: StrictInt = Field(ge=100, le=100_000_000)


class SalonCommissionUpdate(_Request):
    commission_rate_percent: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    note: str | None = Field(default=None, max_length=200)


class PaymentSettingsResponse(BaseModel):
    commission_rate_percent: Decimal | None
    commission_base: CommissionBase | None
    min_payout_paise: int
    policy_version: int
    updated_at: datetime
    #: What a new payment would use right now, and where the rate comes from. Null until a rate is set.
    effective_rate_percent: Decimal | None
    effective_base: CommissionBase | None
    effective_source: RateSource | None


class SalonCommissionResponse(BaseModel):
    salon_id: str
    commission_rate_percent: Decimal | None
    note: str | None
    effective_rate_percent: Decimal | None
    effective_base: CommissionBase | None
    effective_source: RateSource | None
