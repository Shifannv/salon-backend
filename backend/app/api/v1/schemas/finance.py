"""Owner finance cash book API schemas. Money is integer paise; unknown request fields are refused."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_PAISE = 10_000_000_000_00  # one billion rupees: a sanity bound, not a business limit
Paise = Field(gt=0, le=MAX_PAISE)

ExpenseCategory = Literal["supplies", "rent", "utilities", "salary_advance", "maintenance", "other"]
ExpenseMethod = Literal["cash", "non_cash"]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpenseCreateRequest(_Request):
    category: ExpenseCategory
    amount_paise: int = Paise
    payment_method: ExpenseMethod
    occurred_at: datetime
    note: str | None = Field(default=None, max_length=500)


class AdjustmentCreateRequest(_Request):
    direction: Literal["in", "out"]
    amount_paise: int = Paise
    reason: str = Field(min_length=3, max_length=500)
    occurred_at: datetime

    @field_validator("reason")
    @classmethod
    def reason_has_text(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("reason must contain at least 3 characters")
        return value


class DayCloseRequest(_Request):
    actual_cash_paise: int = Field(ge=0, le=MAX_PAISE)
    difference_reason: str | None = Field(default=None, max_length=500)
    # Only for the very first close; later days carry the previous count forward.
    opening_cash_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ExpenseResponse(_Response):
    id: UUID
    entry_type: Literal["expense", "reversal"]
    reverses_id: UUID | None
    category: ExpenseCategory
    amount_paise: int
    payment_method: ExpenseMethod
    occurred_at: datetime
    note: str | None
    created_at: datetime
    reversed: bool = False
    replayed: bool = False
    notice: str = "Expense record. Not a tax invoice or official accounting ledger."


class ExpenseListResponse(_Response):
    expenses: list[ExpenseResponse]
    limit: int
    offset: int


class AdjustmentResponse(_Response):
    id: UUID
    direction: Literal["in", "out"]
    amount_paise: int
    reason: str
    occurred_at: datetime
    created_at: datetime
    replayed: bool = False


class MoneySplit(_Response):
    cash_paise: int
    non_cash_paise: int


class AdjustmentTotals(_Response):
    in_paise: int
    out_paise: int


class DayCloseView(_Response):
    revision: int
    opening_cash_paise: int
    expected_cash_paise: int
    actual_cash_paise: int
    difference_paise: int
    difference_reason: str | None
    closed_at: datetime


class DailyLedgerResponse(_Response):
    date: date
    timezone: str
    status: Literal["open", "closed"]
    gross_completed_sales_paise: int
    cash_collected_paise: int
    non_cash_received_paise: int
    outstanding_due_paise: int
    refunds: MoneySplit
    expenses: MoneySplit
    expenses_total_paise: int
    cash_adjustments: AdjustmentTotals
    opening_cash_paise: int
    # needs_confirmation: the day before was not closed, so opening_cash_paise is only a suggestion.
    opening_cash_source: Literal["previous_close", "entered_at_close", "needs_confirmation", "not_set"]
    expected_closing_cash_paise: int
    close: DayCloseView | None
    # True while a completed booking has no receipt or a refund is still pending: do not show
    # these totals as final.
    needs_review: bool
    # False when the trial or plan has ended: records stay readable, every write is refused.
    can_write: bool = True


class LedgerRangeDay(_Response):
    date: date
    gross_completed_sales_paise: int
    cash_collected_paise: int
    non_cash_received_paise: int
    expenses_paise: int
    status: Literal["open", "closed"]


class LedgerRangeTotals(_Response):
    gross_completed_sales_paise: int
    cash_collected_paise: int
    non_cash_received_paise: int
    expenses_paise: int


class LedgerRangeResponse(_Response):
    days: list[LedgerRangeDay]
    totals: LedgerRangeTotals
    needs_review: bool
