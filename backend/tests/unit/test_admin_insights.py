"""Admin insights: the lapsed-salon queue, per-salon analytics and the bulk offer.

No database: the use case runs over fakes. The SQL itself is guarded lexically here (the same
pitfall tests/test_sql_bind_params.py documents) and needs a real PostgreSQL to execute.
"""

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text
from sqlalchemy.dialects.postgresql.asyncpg import dialect as asyncpg_dialect
from support_subscription import profile

from app.api.v1.schemas.admin_insights import BulkPlanPriceRequest
from app.api.v1.schemas.subscription import PlanPriceSetRequest
from app.application.use_cases.admin_insights import (
    AdminInsightsUseCases,
    _rollup_money,
    _today_ist,
)
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.entities.profile import Role
from app.infrastructure.db.repositories import admin_insights_repository as repo_module

D = Decimal
ADMIN = profile(Role.super_admin, "admin-1")
OWNER = profile(Role.owner, "owner-1")
SALON = "11111111-1111-1111-1111-111111111111"
PLAN = "22222222-2222-2222-2222-222222222222"


def _row(source: str | None, **over: Any) -> dict[str, Any]:
    base = {
        "source": source, "is_total": 1 if source is None else 0, "total": 10, "pending": 1,
        "confirmed": 2, "checked_in": 0, "completed": 5, "cancelled": 1, "rejected": 0,
        "no_show": 1, "customers": 7, "completed_value": D("2500.00"),
    }
    return {**base, **over}


class FakeInsightsRepo:
    def __init__(self) -> None:
        self.salon: dict[str, Any] | None = {"id": SALON, "name": "Glow", "approved_at": None}
        self.bookings = [_row(None), _row("qr_walkin", total=6), _row("app", total=4)]
        self.months: list[dict[str, Any]] = []
        self.missing: list[str] = []
        self.bulk_calls: list[tuple] = []
        self.list_args: dict[str, Any] = {}

    async def list_salon_subscriptions(self, **kw):
        self.list_args = kw
        return []

    async def subscription_summary(self, *, within_days):
        return {"lapsed": 3, "none": 2, "ending_soon": 1}

    async def salon_header(self, salon_id):
        return self.salon

    async def booking_counts(self, salon_id, date_from, date_to):
        return self.bookings

    async def monthly_bookings(self, salon_id, date_from, date_to):
        return []

    async def monthly_money(self, salon_id, date_from, date_to):
        return self.months

    async def find_missing_salons(self, salon_ids):
        return self.missing

    async def bulk_set_plan_price(self, salon_ids, plan_id, price, actor_id, valid_until):
        self.bulk_calls.append((salon_ids, plan_id, price, actor_id, valid_until))
        return len(salon_ids)


class FakePlans:
    async def get_plan(self, plan_id):
        return {"id": plan_id, "price_amount": D("349.00")}


def uc(repo: FakeInsightsRepo | None = None) -> tuple[AdminInsightsUseCases, FakeInsightsRepo]:
    repo = repo or FakeInsightsRepo()
    return AdminInsightsUseCases(repo, FakePlans()), repo


def _month(month: date, currency: str = "INR", **over: Any) -> dict[str, Any]:
    base = {
        "month": month, "currency": currency, "online_collected": D("1000.00"),
        "online_refunded": D("100.00"), "platform_commission_net": D("50.00"),
        "manual_recorded": D("200.00"), "subscription_paid": D("499.00"),
        "online_payment_count": 4, "manual_payment_count": 2,
    }
    return {**base, **over}


# ── access ───────────────────────────────────────────────────────────────────


async def test_only_a_super_admin_can_use_the_insights():
    use, _ = uc()
    today = _today_ist()
    calls = [
        use.list_salon_subscriptions(OWNER, state=None, within_days=7, search=None, limit=50, offset=0),
        use.subscription_summary(OWNER, within_days=7),
        use.salon_analytics(OWNER, SALON, today, today),
        use.bulk_set_plan_price(
            OWNER, salon_ids=[SALON], plan_id=PLAN, price=D("249"),
            offer_discount_percent=None, valid_until=None,
        ),
    ]
    for call in calls:
        with pytest.raises(ForbiddenError):
            await call


# ── analytics ────────────────────────────────────────────────────────────────


async def test_analytics_returns_totals_sources_and_rolled_up_money():
    use, repo = uc()
    repo.months = [_month(date(2026, 9, 1)), _month(date(2026, 10, 1), online_collected=D("500.00"))]
    out = await use.salon_analytics(ADMIN, SALON, date(2026, 9, 1), date(2026, 10, 20))
    assert out["bookings"]["total"] == 10 and out["bookings"]["customers"] == 7
    assert [s["source"] for s in out["by_source"]] == ["app", "qr_walkin"]
    (money,) = out["money"]
    assert money["currency"] == "INR"
    assert money["online_collected"] == D("1500.00")
    assert money["online_payment_count"] == 8
    # net = collected - refunded - commission, the owner earnings formula
    assert money["online_net"] == D("1500.00") - D("200.00") - D("100.00")
    assert len(out["monthly_money"]) == 2
    assert out["monthly_money"][1]["online_net"] == D("500.00") - D("100.00") - D("50.00")


async def test_analytics_accepts_a_single_day_and_a_whole_lifetime():
    use, _ = uc()
    today = _today_ist()
    assert (await use.salon_analytics(ADMIN, SALON, today, today))["date_from"] == today
    assert (await use.salon_analytics(ADMIN, SALON, date(2020, 1, 1), today))["date_to"] == today


async def test_analytics_rejects_a_reversed_range():
    use, _ = uc()
    with pytest.raises(ValidationError):
        await use.salon_analytics(ADMIN, SALON, date(2026, 10, 20), date(2026, 10, 1))


async def test_analytics_rejects_an_end_date_in_the_future():
    use, _ = uc()
    with pytest.raises(ValidationError):
        await use.salon_analytics(ADMIN, SALON, _today_ist(), _today_ist() + timedelta(days=1))


async def test_analytics_for_an_unknown_salon_is_not_found():
    use, repo = uc()
    repo.salon = None
    with pytest.raises(NotFoundError):
        await use.salon_analytics(ADMIN, SALON, date(2026, 10, 1), date(2026, 10, 2))


def test_money_is_never_added_across_currencies():
    rolled = _rollup_money([_month(date(2026, 10, 1), "INR"), _month(date(2026, 10, 1), "USD")])
    assert [r["currency"] for r in rolled] == ["INR", "USD"]
    assert all(r["online_collected"] == D("1000.00") for r in rolled)


def test_no_payments_means_no_money_rows():
    assert _rollup_money([]) == []


# ── queue ────────────────────────────────────────────────────────────────────


async def test_the_queue_passes_filters_through_and_trims_the_search():
    use, repo = uc()
    await use.list_salon_subscriptions(
        ADMIN, state="lapsed", within_days=14, search="  glow ", limit=20, offset=40
    )
    assert repo.list_args == {
        "state": "lapsed", "within_days": 14, "search": "glow", "limit": 20, "offset": 40,
    }


async def test_the_summary_reports_each_state():
    use, _ = uc()
    assert await use.subscription_summary(ADMIN, within_days=7) == {
        "within_days": 7, "lapsed": 3, "none": 2, "ending_soon": 1,
    }


# ── bulk offer ───────────────────────────────────────────────────────────────


async def test_a_bulk_offer_computes_the_price_once_and_applies_it_to_every_salon():
    use, repo = uc()
    out = await use.bulk_set_plan_price(
        ADMIN, salon_ids=[SALON, "33333333-3333-3333-3333-333333333333"], plan_id=PLAN,
        price=None, offer_discount_percent=20, valid_until=None,
    )
    assert out["applied"] == 2 and out["price_amount"] == D("279.20")
    assert repo.bulk_calls[0][2] == D("279.20") and repo.bulk_calls[0][3] == "admin-1"


async def test_a_bulk_offer_follows_the_same_price_rules_as_a_single_offer():
    use, repo = uc()
    with pytest.raises(ValidationError):
        await use.bulk_set_plan_price(
            ADMIN, salon_ids=[SALON], plan_id=PLAN, price=D("349.00"),
            offer_discount_percent=None, valid_until=None,
        )
    assert repo.bulk_calls == []


async def test_a_bulk_offer_cannot_end_in_the_past():
    use, repo = uc()
    with pytest.raises(ValidationError):
        await use.bulk_set_plan_price(
            ADMIN, salon_ids=[SALON], plan_id=PLAN, price=D("249"), offer_discount_percent=None,
            valid_until=datetime.now(UTC) - timedelta(minutes=1),
        )
    assert repo.bulk_calls == []


async def test_a_bulk_offer_applies_to_none_when_any_salon_is_unknown():
    use, repo = uc()
    repo.missing = ["33333333-3333-3333-3333-333333333333"]
    with pytest.raises(ValidationError) as err:
        await use.bulk_set_plan_price(
            ADMIN, salon_ids=[SALON, repo.missing[0]], plan_id=PLAN, price=D("249"),
            offer_discount_percent=None, valid_until=None,
        )
    assert err.value.details == {"salon_ids": repo.missing}
    assert repo.bulk_calls == []


async def test_a_bulk_offer_for_an_unknown_plan_is_a_clean_not_found():
    class NoPlans:
        async def get_plan(self, plan_id):
            raise NotFoundError("Subscription plan not found")

    use = AdminInsightsUseCases(FakeInsightsRepo(), NoPlans())
    with pytest.raises(NotFoundError):
        await use.bulk_set_plan_price(
            ADMIN, salon_ids=[SALON], plan_id=PLAN, price=D("249"),
            offer_discount_percent=None, valid_until=None,
        )


# ── request schema ───────────────────────────────────────────────────────────


def test_an_offer_end_without_a_timezone_is_refused_not_a_server_error():
    with pytest.raises(PydanticValidationError):
        BulkPlanPriceRequest(salon_ids=[SALON], plan_id=PLAN, price_amount="249", valid_until="2099-12-01T00:00:00")
    with pytest.raises(PydanticValidationError):
        PlanPriceSetRequest(price_amount="249", valid_until="2099-12-01T00:00:00")
    ok = BulkPlanPriceRequest(salon_ids=[SALON], plan_id=PLAN, price_amount="249", valid_until="2099-12-01T00:00:00+05:30")
    assert ok.valid_until is not None and ok.valid_until.utcoffset() is not None


def test_the_bulk_request_needs_exactly_one_offer_input():
    with pytest.raises(PydanticValidationError):
        BulkPlanPriceRequest(salon_ids=[SALON], plan_id=PLAN)
    with pytest.raises(PydanticValidationError):
        BulkPlanPriceRequest(salon_ids=[SALON], plan_id=PLAN, price_amount="249", offer_discount_percent=20)


def test_the_bulk_request_rejects_repeats_empty_and_oversized_lists_and_bad_ids():
    with pytest.raises(PydanticValidationError):
        BulkPlanPriceRequest(salon_ids=[SALON, SALON], plan_id=PLAN, price_amount="249")
    with pytest.raises(PydanticValidationError):
        BulkPlanPriceRequest(salon_ids=[], plan_id=PLAN, price_amount="249")
    with pytest.raises(PydanticValidationError):
        BulkPlanPriceRequest(salon_ids=["not-a-uuid"], plan_id=PLAN, price_amount="249")
    too_many = [f"00000000-0000-0000-0000-{i:012d}" for i in range(101)]
    with pytest.raises(PydanticValidationError):
        BulkPlanPriceRequest(salon_ids=too_many, plan_id=PLAN, price_amount="249")


# ── SQL guards (no database) ─────────────────────────────────────────────────


def test_no_bind_parameter_is_followed_by_a_postgres_cast():
    source = Path(repo_module.__file__).read_text(encoding="utf-8")
    assert re.search(r":[a-zA-Z_][a-zA-Z0-9_]*::", source) is None


def test_the_classification_query_compiles_for_the_production_driver():
    statement = text(repo_module._CLASSIFIED + "select * from classified where state = cast(:state as text)")
    compiled = statement.compile(dialect=asyncpg_dialect())
    assert {"search", "within", "state"} <= set(compiled.params)
