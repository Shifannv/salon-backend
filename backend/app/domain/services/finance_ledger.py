"""Owner cash book rules. Pure functions: all money is integer paise, nothing touches a database.

The Daily Ledger is an operational cash book, not tax accounting and not a profit figure. Every
total is derived at read time from immutable records; completed sales, cash received, UPI
received, refunds, expenses and amounts still due stay separate numbers.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

FINANCE_FEATURE = "daily_ledger"
MAX_RANGE_DAYS = 93


@dataclass(frozen=True)
class TrialState:
    """The salon's free-trial window, as stored in ``salon_access``."""

    started_at: datetime | None
    ends_at: datetime | None
    booking_limit: int | None
    bookings_counted: int | None
    limit_reached_at: datetime | None

    def active(self, now: datetime) -> bool:
        if self.started_at is None or self.ends_at is None or self.limit_reached_at is not None:
            return False
        if self.booking_limit is not None and (self.bookings_counted or 0) >= self.booking_limit:
            return False
        return self.ends_at > now


def finance_allowed(
    *, features: dict[str, Any], entitlement_active: bool, trial: TrialState | None, now: datetime
) -> bool:
    """A paid plan must include ``daily_ledger``; a salon still on its free trial has Growth access.

    Trial salons have no subscription row, so their feature list is empty. Without the trial
    branch every new owner would be locked out of the cash book.
    """

    if entitlement_active and features.get(FINANCE_FEATURE) is True:
        return True
    return trial is not None and not entitlement_active and trial.active(now)


def local_day_bounds(local_date: date, timezone: str) -> tuple[datetime, datetime]:
    """The half-open UTC interval [start, end) covering one salon-local calendar day."""

    zone = ZoneInfo(timezone)
    start = datetime(local_date.year, local_date.month, local_date.day, tzinfo=zone)
    end = datetime.combine(local_date + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return start.astimezone(UTC), end.astimezone(UTC)


def month_bounds(month: str, timezone: str) -> tuple[datetime, datetime]:
    """The half-open UTC interval [start, end) covering one salon-local calendar month ("2026-10")."""

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("month must look like 2026-10")
    year, number = int(month[:4]), int(month[5:])
    zone = ZoneInfo(timezone)
    start = datetime(year, number, 1, tzinfo=zone)
    following = datetime(year + 1, 1, 1, tzinfo=zone) if number == 12 else datetime(year, number + 1, 1, tzinfo=zone)
    return start.astimezone(UTC), following.astimezone(UTC)


def rule_applies_on(frequency: str, start: date, day: date) -> bool:
    """Whether a repeating expense falls on ``day``. Weekly repeats on the start date's weekday, monthly
    on its day of the month (a shorter month uses its last day). Mirrors the owner app exactly."""

    if day < start:
        return False
    if frequency == "daily":
        return True
    if frequency == "weekly":
        return (day - start).days % 7 == 0
    if frequency == "monthly":
        return day.day == min(start.day, calendar.monthrange(day.year, day.month)[1])
    return False


def today_in(timezone: str, now: datetime) -> date:
    return now.astimezone(ZoneInfo(timezone)).date()


def expected_closing_cash(
    *,
    opening_cash: int,
    cash_collected: int,
    cash_refunds: int,
    cash_expenses: int,
    adjustments_in: int = 0,
    adjustments_out: int = 0,
) -> int:
    """opening + cash collected - cash refunds - cash expenses +/- audited adjustments."""

    return (
        opening_cash + cash_collected - cash_refunds - cash_expenses + adjustments_in - adjustments_out
    )


def close_difference(expected: int, actual: int, reason: str | None) -> int:
    """Counted minus expected. Returns the difference; the caller refuses a missing reason."""

    return actual - expected


def reason_is_written(reason: str | None) -> bool:
    return len((reason or "").strip()) >= 3
