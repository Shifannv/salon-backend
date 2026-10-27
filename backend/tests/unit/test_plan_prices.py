"""Per-salon plan prices and the website checkout address (no database: SQL is covered by the
real-PostgreSQL test in tests/integration/test_subscription_billing_sql.py)."""

from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError
from support_subscription import (
    FakeBillingRepo,
    FakeProvider,
    owner,
    profile,
    resolver_for,
    sub_settings,
)

from app.api.v1.schemas.subscription import PlanPriceSetRequest
from app.application.use_cases.subscription import SubscriptionPlanUseCases
from app.application.use_cases.subscription_billing import SubscriptionBillingUseCases
from app.core.config import Settings
from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Role

D = Decimal


class FakePlanRepo:
    def __init__(self) -> None:
        self.set_calls: list[tuple] = []
        self.cleared: list[tuple] = []

    async def list_salon_plan_prices(self, salon_id: str) -> list[dict[str, Any]]:
        return []

    async def set_salon_plan_price(self, salon_id, plan_id, price, actor_id):
        self.set_calls.append((salon_id, plan_id, price, actor_id))
        return {"salon_id": salon_id, "plan_id": plan_id, "price_amount": price}

    async def clear_salon_plan_price(self, salon_id, plan_id, actor_id):
        self.cleared.append((salon_id, plan_id, actor_id))


def billing():
    repo = FakeBillingRepo()
    settings = sub_settings()
    return SubscriptionBillingUseCases(repo, resolver_for(FakeProvider(settings), settings), settings, repo), repo


async def test_an_owner_sees_the_plan_list_for_their_own_salon():
    uc, repo = billing()
    plans = await uc.list_plans(owner())
    assert repo.plan_list_calls == ["salon-1"]
    assert plans and plans[0]["custom_price"] is False
    assert plans[0]["default_price_amount"] == plans[0]["price_amount"]


async def test_an_admin_sees_plan_prices_not_any_one_salons_prices():
    uc, repo = billing()
    await uc.list_plans(profile(Role.super_admin, "admin-1"))
    assert repo.plan_list_calls == [None]


async def test_a_customer_cannot_list_purchasable_plans():
    uc, _ = billing()
    with pytest.raises(ForbiddenError):
        await uc.list_plans(profile(Role.customer, "c-1"))


def test_config_carries_the_website_address_when_one_is_configured():
    settings = sub_settings(subscription_website_url="https://salones.example/subscribe")
    uc = SubscriptionBillingUseCases(None, resolver_for(FakeProvider(settings), settings), settings)
    assert uc.config()["checkout_url"] == "https://salones.example/subscribe"


@pytest.mark.parametrize("value, expected", [
    ("https://salones.example/subscribe", "https://salones.example/subscribe"),
    ("  https://salones.example  ", "https://salones.example"),
    ("http://localhost:3000/subscribe", "http://localhost:3000/subscribe"),
    ("", None),
    (None, None),
])
def test_website_address_accepts_https_or_local_only(value, expected):
    assert Settings(_env_file=None, environment="test", subscription_website_url=value).subscription_website_url == expected


@pytest.mark.parametrize("value", ["http://salones.example", "javascript:alert(1)", "ftp://x.example"])
def test_website_address_rejects_other_schemes(value):
    with pytest.raises(PydanticValidationError):
        Settings(_env_file=None, environment="test", subscription_website_url=value)


async def test_only_a_super_admin_can_set_or_clear_a_salon_price():
    uc = SubscriptionPlanUseCases(FakePlanRepo())
    for actor in (owner(), profile(Role.customer, "c-1"), profile(Role.staff, "s-1")):
        with pytest.raises(ForbiddenError):
            await uc.set_salon_price(actor, "s", "p", D("100"))
        with pytest.raises(ForbiddenError):
            await uc.clear_salon_price(actor, "s", "p")
        with pytest.raises(ForbiddenError):
            await uc.list_salon_prices(actor, "s")


async def test_a_super_admin_sets_a_price_and_the_change_is_attributed_to_them():
    repo = FakePlanRepo()
    admin = profile(Role.super_admin, "admin-1")
    row = await SubscriptionPlanUseCases(repo).set_salon_price(admin, "salon-1", "plan-1", D("249.00"))
    assert repo.set_calls == [("salon-1", "plan-1", D("249.00"), "admin-1")]
    assert row["price_amount"] == D("249.00")
    await SubscriptionPlanUseCases(repo).clear_salon_price(admin, "salon-1", "plan-1")
    assert repo.cleared == [("salon-1", "plan-1", "admin-1")]


@pytest.mark.parametrize("price", [D("0"), D("-1")])
async def test_a_price_must_be_above_zero(price):
    repo = FakePlanRepo()
    with pytest.raises(ValidationError):
        await SubscriptionPlanUseCases(repo).set_salon_price(profile(Role.super_admin, "a"), "s", "p", price)
    assert repo.set_calls == []


@pytest.mark.parametrize("price", ["0", "-5", "1.234", "99999999999"])
def test_the_request_rejects_unusable_prices(price):
    with pytest.raises(PydanticValidationError):
        PlanPriceSetRequest(price_amount=price)


def test_the_request_accepts_whole_rupees_and_paise():
    assert PlanPriceSetRequest(price_amount="249").price_amount == D("249")
    assert PlanPriceSetRequest(price_amount="249.50").price_amount == D("249.50")
