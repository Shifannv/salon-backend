"""Provider-agnostic subscription promotion eligibility.

Pure Python — no imports from infrastructure, FastAPI, or payment SDKs.
"""

from datetime import datetime

from app.domain.entities.subscription import SubscriptionStatus


def is_subscription_promotion_active(
    status: str | SubscriptionStatus,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
    grace_period_end: datetime | None,
    now: datetime | None = None,
) -> bool:
    """Mirror the Postgres ``is_subscription_promotion_active`` function.

    - ``active`` / ``trialing``: eligible while inside ``[current_period_start, current_period_end)``.
    - ``cancelled``: eligible until ``current_period_end``.
    - ``past_due``: eligible until ``grace_period_end``.
    - ``expired`` / ``suspended`` / ``pending``: never eligible.
    - Invalid or missing dates always return False.
    """

    if now is None:
        now = datetime.now(tz=current_period_start.tzinfo if current_period_start else None)

    if status in (SubscriptionStatus.active, SubscriptionStatus.trialing):
        return (
            current_period_start is not None
            and current_period_end is not None
            and current_period_start <= now < current_period_end
        )

    if status == SubscriptionStatus.cancelled:
        return current_period_end is not None and now < current_period_end

    if status == SubscriptionStatus.past_due:
        return grace_period_end is not None and now < grace_period_end

    return False
