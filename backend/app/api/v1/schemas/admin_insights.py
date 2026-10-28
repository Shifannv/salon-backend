"""Admin insight schemas: which salons need attention, and a salon's performance over a range."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

SubscriptionState = Literal["lapsed", "none", "ending_soon"]
BookingSource = Literal["app", "qr_walkin", "manual_walkin"]


# ── Salons that need a subscription decision ─────────────────────────────────


class SalonSubscriptionRow(BaseModel):
    salon_id: str
    salon_name: str
    city: str | None = None
    owner_name: str | None = None
    owner_email: str | None = None
    owner_phone: str | None = None
    state: Literal["lapsed", "none", "ending_soon", "ok"]
    subscription_status: str | None = None
    plan_code: str | None = None
    plan_name: str | None = None
    current_period_end: datetime | None = None
    grace_period_end: datetime | None = None
    cancelled_at: datetime | None = None
    trial_ends_at: datetime | None = None
    trial_bookings_counted: int | None = None
    trial_booking_limit: int | None = None
    trial_ended_reason: str | None = None
    ends_at: datetime | None = Field(
        default=None, description="When paid or trial access ended, or will end."
    )
    days_since_end: int | None = None
    days_until_end: int | None = None

    @field_validator("salon_id", mode="before")
    @classmethod
    def stringify_id(cls, v: object) -> str:
        return str(v)


class SalonSubscriptionSummary(BaseModel):
    within_days: int
    lapsed: int
    none: int
    ending_soon: int


# ── Per-salon analytics ──────────────────────────────────────────────────────


class BookingCounts(BaseModel):
    total: int
    pending: int
    confirmed: int
    checked_in: int
    completed: int
    cancelled: int
    rejected: int
    no_show: int
    customers: int = Field(description="Distinct customers (account or phone) in the range.")
    completed_value: Decimal = Field(max_digits=14, decimal_places=2)


class SourceBookingCounts(BookingCounts):
    source: BookingSource


class MoneyTotals(BaseModel):
    currency: str
    online_collected: Decimal
    online_refunded: Decimal
    platform_commission_net: Decimal
    online_net: Decimal
    manual_recorded: Decimal
    subscription_paid: Decimal
    online_payment_count: int
    manual_payment_count: int


class MonthlyMoney(MoneyTotals):
    month: date


class MonthlyBookings(BaseModel):
    month: date
    total: int
    completed: int
    cancelled: int
    no_show: int


class SalonAnalyticsResponse(BaseModel):
    salon_id: str
    salon_name: str
    approved_at: datetime | None = None
    date_from: date
    date_to: date
    bookings: BookingCounts
    by_source: list[SourceBookingCounts]
    money: list[MoneyTotals]
    monthly_bookings: list[MonthlyBookings]
    monthly_money: list[MonthlyMoney]
    note: str = (
        "Bookings are counted by booking date and money by payment date, both in Asia/Kolkata. "
        "Income is derived from the payment ledger; provider fees and taxes are not included."
    )

    @field_validator("salon_id", mode="before")
    @classmethod
    def stringify_id(cls, v: object) -> str:
        return str(v)


# ── Bulk offer ───────────────────────────────────────────────────────────────


class BulkPlanPriceRequest(BaseModel):
    """One offer for many salons at once. Same rules as a single salon offer."""

    salon_ids: list[UUID] = Field(min_length=1, max_length=100)
    plan_id: UUID
    price_amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    offer_discount_percent: int | None = Field(default=None, ge=1, le=99)
    valid_until: AwareDatetime | None = None

    @model_validator(mode="after")
    def check_request(self) -> "BulkPlanPriceRequest":
        if (self.price_amount is None) == (self.offer_discount_percent is None):
            raise ValueError("Provide exactly one of price_amount or offer_discount_percent")
        if len(set(self.salon_ids)) != len(self.salon_ids):
            raise ValueError("salon_ids must not repeat")
        return self


class BulkPlanPriceResponse(BaseModel):
    applied: int
    plan_id: str
    price_amount: Decimal
    valid_until: datetime | None = None
