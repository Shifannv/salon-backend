"""Owner wallet rules: what is available, what a request may ask for. Pure Python, integer paise.

The wallet is not a stored balance. What the salon earned online (collected, less the platform
commission, less refunds) minus what it has already asked for or been paid is what is left to ask
for. Rejecting or cancelling a request therefore puts the money back with no extra bookkeeping.
"""

from __future__ import annotations

from datetime import date, timedelta

# The smallest amount one request may ask for. A default for the platform to confirm: it only
# stops requests too small to be worth paying by hand.
MIN_PAYOUT_PAISE = 10_000
# One request may not be set for a day further away than this.
MAX_PAYOUT_DAYS_AHEAD = 60
# Money asked for in one request: a sanity ceiling, not a business limit.
MAX_PAYOUT_PAISE = 100_000_000

PAYOUT_STATUSES = ("requested", "paid", "rejected", "cancelled")
# Statuses that still hold the money back from the available balance.
HOLDING_STATUSES = ("requested", "paid")


def net_online_paise(*, collected: int, commission: int, refunded: int, commission_reversed: int) -> int:
    """The salon's share of online payments: collected less commission and refunds, plus any
    commission handed back on a refund. Never negative."""

    return max(collected - commission - refunded + commission_reversed, 0)


def available_paise(*, net_online: int, requested: int, paid: int) -> int:
    """What can still be asked for. Floors at zero: a refund after a payout must not show a debt."""

    return max(net_online - requested - paid, 0)


class PayoutDateProblem(ValueError):
    """The day asked for is not allowed."""


def check_payout_day(day: date, today: date) -> None:
    if day < today:
        raise PayoutDateProblem("The payout day cannot be in the past")
    if day > today + timedelta(days=MAX_PAYOUT_DAYS_AHEAD):
        raise PayoutDateProblem(f"The payout day can be at most {MAX_PAYOUT_DAYS_AHEAD} days ahead")


def can_cancel(status: str) -> bool:
    """Only a request still waiting to be paid can be taken back."""

    return status == "requested"
