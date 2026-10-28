"""Monthly messaging quota arithmetic. Pure functions; storage lives behind a port."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

# Premium: provider-accepted outbound sends per salon per local calendar month, no carry-over.
DEFAULT_MONTHLY_CAP = 300


@dataclass(frozen=True)
class QuotaWindow:
    """One local calendar month, as UTC instants, plus the local date the quota resets."""

    start: datetime
    end: datetime
    reset_date: date


def month_window(now: datetime, timezone: str) -> QuotaWindow:
    zone = ZoneInfo(timezone)
    local = now.astimezone(zone)
    first = datetime(local.year, local.month, 1, tzinfo=zone)
    next_year, next_month = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
    following = datetime(next_year, next_month, 1, tzinfo=zone)
    return QuotaWindow(
        start=first.astimezone(UTC), end=following.astimezone(UTC), reset_date=following.date()
    )


def remaining(used: int, cap: int) -> int:
    return max(cap - used, 0)


def has_quota(used: int, cap: int) -> bool:
    return used < cap
