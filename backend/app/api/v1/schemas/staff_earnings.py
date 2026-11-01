"""Staff earnings API schemas (owner only). Money is integer paise; unknown request fields are refused."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

CommissionType = Literal["NONE", "FIXED_PER_SERVICE", "PERCENT_OF_SERVICE_VALUE"]
MAX_FIXED_PAISE = 10_000_000_00  # ten million rupees per service: a sanity bound, not a business limit


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CommissionRuleCreateRequest(_Request):
    staff_id: UUID | None = None
    service_id: UUID | None = None
    commission_type: CommissionType
    rate_basis_points: int | None = Field(default=None, ge=0, le=10_000)
    fixed_amount_paise: int | None = Field(default=None, ge=0, le=MAX_FIXED_PAISE)
    effective_from: datetime | None = None

    @model_validator(mode="after")
    def shape_matches_type(self) -> "CommissionRuleCreateRequest":
        none = self.commission_type == "NONE"
        fixed = self.commission_type == "FIXED_PER_SERVICE"
        if none and (self.rate_basis_points is not None or self.fixed_amount_paise is not None):
            raise ValueError("NONE takes no rate or amount")
        if fixed and (self.fixed_amount_paise is None or self.rate_basis_points is not None):
            raise ValueError("FIXED_PER_SERVICE takes only fixed_amount_paise")
        if self.commission_type == "PERCENT_OF_SERVICE_VALUE" and (
            self.rate_basis_points is None or self.fixed_amount_paise is not None
        ):
            raise ValueError("PERCENT_OF_SERVICE_VALUE takes only rate_basis_points")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a time zone")
        return self


class CommissionRuleResponse(_Response):
    id: UUID
    staff_id: UUID | None
    service_id: UUID | None
    version: int
    commission_type: CommissionType
    rate_basis_points: int | None
    fixed_amount_paise: int | None
    effective_from: datetime
    created_at: datetime
    replayed: bool = False


class CommissionRuleListResponse(_Response):
    """The rule in force for each scope (its newest version)."""

    rules: list[CommissionRuleResponse]
    can_write: bool


class ServiceStaffRequest(_Request):
    staff_id: UUID


class ServiceStaffResponse(_Response):
    booking_id: UUID
    service_id: UUID
    staff_id: UUID
    revision: int


class StaffEarningsLine(_Response):
    staff_id: UUID
    staff_name: str
    services_completed: int
    service_value_paise: int
    commission_paise: int
    collected_cash_paise: int
    collected_upi_paise: int


class StaffEarningsResponse(_Response):
    """What each staff member's completed services earned them in a salon-local date range."""

    from_date: date
    to_date: date
    staff: list[StaffEarningsLine]
    services_completed: int
    service_value_paise: int
    commission_paise: int
    collected_cash_paise: int
    collected_upi_paise: int


class BookingLine(_Response):
    service_name: str
    staff_name: str
    service_value_paise: int


class StaffServiceItem(_Response):
    booking_id: UUID
    service_id: UUID
    service_name: str
    customer_first_name: str
    completed_at: datetime
    service_value_paise: int
    commission_paise: int
    # What the customer paid on the whole booking, and this service's share of it (salon receipts, F19).
    booking_cash_paise: int
    booking_upi_paise: int
    collected_cash_paise: int
    collected_upi_paise: int
    booking_lines: list[BookingLine]


class StaffDetailResponse(_Response):
    staff_id: UUID
    staff_name: str
    from_date: date
    to_date: date
    services_completed: int
    service_value_paise: int
    commission_paise: int
    collected_cash_paise: int
    collected_upi_paise: int
    history: list[StaffServiceItem]
    next_cursor: str | None


class ServiceStaffLine(_Response):
    service_id: UUID
    service_name: str
    staff_id: UUID
    staff_name: str


class ServiceStaffListResponse(_Response):
    """Who is doing each service of a booking now. ``can_change`` is false once the booking is finished."""

    booking_id: UUID
    lines: list[ServiceStaffLine]
    can_change: bool
