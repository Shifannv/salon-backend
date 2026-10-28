"""Admin insight use cases — which salons need a subscription decision, per-salon performance,
and one offer for many salons. Super admin only."""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.application.use_cases.subscription import resolve_offer_price
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.admin_insights_repository import AdminInsightsRepo
from app.infrastructure.db.repositories.subscription_repository import SubscriptionPlanRepo

# The platform's business calendar. India has no daylight saving, so a fixed offset is exact.
_IST = timezone(timedelta(hours=5, minutes=30))
_ZERO = Decimal("0.00")
_COUNT_FIELDS = (
    "total", "pending", "confirmed", "checked_in", "completed", "cancelled", "rejected",
    "no_show", "customers",
)


def _assert_admin(actor: Profile) -> None:
    if actor.role != Role.super_admin:
        raise ForbiddenError("Super admin required")


def _today_ist() -> date:
    return datetime.now(UTC).astimezone(_IST).date()


def _counts(row: dict[str, Any]) -> dict[str, Any]:
    return {**{f: int(row[f]) for f in _COUNT_FIELDS}, "completed_value": Decimal(row["completed_value"])}


def _rollup_money(months: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-currency totals from the monthly rows. Counts and amounts add up; nothing is distinct."""

    by_currency: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "online_collected": _ZERO, "online_refunded": _ZERO, "platform_commission_net": _ZERO,
            "manual_recorded": _ZERO, "subscription_paid": _ZERO,
            "online_payment_count": 0, "manual_payment_count": 0,
        }
    )
    for m in months:
        t = by_currency[m["currency"]]
        for f in ("online_collected", "online_refunded", "platform_commission_net",
                  "manual_recorded", "subscription_paid"):
            t[f] += Decimal(m[f])
        t["online_payment_count"] += int(m["online_payment_count"])
        t["manual_payment_count"] += int(m["manual_payment_count"])
    return [
        {"currency": cur, **t,
         "online_net": t["online_collected"] - t["online_refunded"] - t["platform_commission_net"]}
        for cur, t in sorted(by_currency.items())
    ]


class AdminInsightsUseCases:
    def __init__(self, repo: AdminInsightsRepo, plans: SubscriptionPlanRepo) -> None:
        self.repo = repo
        self.plans = plans

    async def list_salon_subscriptions(
        self, actor: Profile, *, state: str | None, within_days: int,
        search: str | None, limit: int, offset: int,
    ) -> list[dict[str, Any]]:
        _assert_admin(actor)
        return await self.repo.list_salon_subscriptions(
            state=state, within_days=within_days, search=search.strip() if search else None,
            limit=limit, offset=offset,
        )

    async def subscription_summary(self, actor: Profile, *, within_days: int) -> dict[str, Any]:
        _assert_admin(actor)
        counts = await self.repo.subscription_summary(within_days=within_days)
        return {"within_days": within_days, **counts}

    async def salon_analytics(
        self, actor: Profile, salon_id: str, date_from: date, date_to: date
    ) -> dict[str, Any]:
        """Any range the admin picks: one day up to the salon's whole life."""

        _assert_admin(actor)
        if date_from > date_to:
            raise ValidationError("The start date must not be after the end date")
        if date_to > _today_ist():
            raise ValidationError("The end date cannot be in the future")
        salon = await self.repo.salon_header(salon_id)
        if salon is None:
            raise NotFoundError("Salon not found")

        rows = await self.repo.booking_counts(salon_id, date_from, date_to)
        total = next((r for r in rows if r["is_total"]), None)
        if total is None:  # defensive: the grand-total group always exists
            raise NotFoundError("No analytics available")
        by_source = [
            {"source": r["source"], **_counts(r)}
            for r in sorted((r for r in rows if not r["is_total"]), key=lambda r: r["source"])
        ]
        monthly_money = await self.repo.monthly_money(salon_id, date_from, date_to)
        monthly_bookings = await self.repo.monthly_bookings(salon_id, date_from, date_to)
        return {
            "salon_id": salon["id"],
            "salon_name": salon["name"],
            "approved_at": salon["approved_at"],
            "date_from": date_from,
            "date_to": date_to,
            "bookings": _counts(total),
            "by_source": by_source,
            "money": _rollup_money(monthly_money),
            "monthly_bookings": monthly_bookings,
            "monthly_money": [
                {**m, "online_net": Decimal(m["online_collected"]) - Decimal(m["online_refunded"])
                 - Decimal(m["platform_commission_net"])}
                for m in monthly_money
            ],
        }

    async def bulk_set_plan_price(
        self, actor: Profile, *, salon_ids: list[UUID], plan_id: UUID,
        price: Decimal | None, offer_discount_percent: int | None, valid_until: datetime | None,
    ) -> dict[str, Any]:
        """One offer for many salons. Validated up front, then applied all-or-nothing."""

        _assert_admin(actor)
        if valid_until is not None and valid_until <= datetime.now(UTC):
            raise ValidationError("An offer must end in the future")
        plan = await self.plans.get_plan(str(plan_id))
        final_price = resolve_offer_price(
            Decimal(str(plan["price_amount"])), price, offer_discount_percent
        )
        ids = [str(s) for s in salon_ids]
        missing = await self.repo.find_missing_salons(ids)
        if missing:
            raise ValidationError("Some salons were not found", details={"salon_ids": missing})
        applied = await self.repo.bulk_set_plan_price(
            ids, str(plan_id), final_price, str(actor.id), valid_until
        )
        return {
            "applied": applied, "plan_id": str(plan_id), "price_amount": final_price,
            "valid_until": valid_until,
        }
