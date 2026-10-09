"""Subscription foundation unit tests."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.subscription import (
    ManualSubscriptionCreateRequest,
    PlanCreateRequest,
    PlanResponse,
    SubscriptionResponse,
)
from app.core.config import Settings
from app.domain.entities.subscription import (
    NON_TERMINAL_STATUSES,
    TERMINAL_STATUSES,
    SubscriptionStatus,
)
from app.domain.services.subscription_eligibility import (
    is_subscription_promotion_active,
)

# ── Eligibility logic ────────────────────────────────────────────────────────


_now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
_period_start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
_period_end = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
_grace_end = datetime(2026, 6, 20, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_active_trialing_eligible_during_period(status):
    assert is_subscription_promotion_active(
        status, _period_start, _period_end, None, _now
    )


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_active_trialing_ineligible_outside_period(status):
    past = _period_end + timedelta(days=1)
    assert not is_subscription_promotion_active(
        status, _period_start, _period_end, None, past
    )


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_active_trialing_ineligible_with_null_dates(status):
    assert not is_subscription_promotion_active(status, None, None, None, _now)
    assert not is_subscription_promotion_active(status, _period_start, None, None, _now)
    assert not is_subscription_promotion_active(status, None, _period_end, None, _now)


def test_cancelled_eligible_until_period_end():
    assert is_subscription_promotion_active(
        "cancelled", _period_start, _period_end, None, _now
    )


def test_cancelled_ineligible_after_period_end():
    past = _period_end + timedelta(days=1)
    assert not is_subscription_promotion_active(
        "cancelled", _period_start, _period_end, None, past
    )


def test_cancelled_ineligible_with_null_period_end():
    assert not is_subscription_promotion_active(
        "cancelled", _period_start, None, None, _now
    )


def test_past_due_eligible_during_grace():
    assert is_subscription_promotion_active(
        "past_due", None, None, _grace_end, _now
    )


def test_past_due_ineligible_after_grace():
    past = _grace_end + timedelta(days=1)
    assert not is_subscription_promotion_active(
        "past_due", None, None, _grace_end, past
    )


def test_past_due_ineligible_with_null_grace():
    assert not is_subscription_promotion_active(
        "past_due", None, None, None, _now
    )


@pytest.mark.parametrize("status", ["expired", "suspended", "pending"])
def test_never_eligible_statuses(status):
    assert not is_subscription_promotion_active(
        status, _period_start, _period_end, _grace_end, _now
    )


# ── Domain enums ─────────────────────────────────────────────────────────────


def test_terminal_and_non_terminal_partitions():
    all_statuses = frozenset(SubscriptionStatus)
    assert TERMINAL_STATUSES | NON_TERMINAL_STATUSES == all_statuses
    assert TERMINAL_STATUSES & NON_TERMINAL_STATUSES == frozenset()


# ── Schema validation ────────────────────────────────────────────────────────


def test_plan_create_request_rejects_bad_values():
    with pytest.raises(ValidationError):
        PlanCreateRequest(code="", name="Test")
    with pytest.raises(ValidationError):
        PlanCreateRequest(code="ok", name="Test", ranking_weight=-1)
    with pytest.raises(ValidationError):
        PlanCreateRequest(code="ok", name="Test", ranking_weight=100001)


def test_plan_response_stringifies_id():
    from uuid import UUID

    uid = UUID(int=1)
    resp = PlanResponse(
        id=uid, code="basic", name="Basic", tier=0, ranking_weight=0,
        price_amount=0, currency="INR", billing_interval="monthly",
        is_active=True, created_at=_now, updated_at=_now,
    )
    assert resp.id == str(uid)


def test_test_subscription_rejects_terminal_status():
    with pytest.raises(ValidationError):
        ManualSubscriptionCreateRequest(
            salon_id="x", plan_id="y", status="expired"
        )


def test_subscription_response_does_not_expose_provider_fields():
    fields = set(SubscriptionResponse.model_fields.keys())
    assert "provider_name" not in fields
    assert "provider_customer_reference" not in fields
    assert "provider_subscription_reference" not in fields


# ── Config ───────────────────────────────────────────────────────────────────


def test_subscription_provider_defaults_to_none():
    s = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        environment="test",
    )
    assert s.subscription_provider == "none"


# ── Public response privacy ──────────────────────────────────────────────────


def test_public_salon_response_has_no_subscription_fields():
    from app.api.v1.schemas.platform import SalonSummaryResponse

    fields = set(SalonSummaryResponse.model_fields.keys())
    for forbidden in (
        "display_priority", "ranking_weight", "subscription_status",
        "plan_code", "plan_tier", "billing_interval", "price_amount",
    ):
        assert forbidden not in fields, f"{forbidden} leaked into public response"


# ── Use case authorization ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_non_admin_cannot_manage_plans():
    from unittest.mock import AsyncMock

    from app.application.use_cases.subscription import SubscriptionPlanUseCases
    from app.core.exceptions import ForbiddenError
    from app.domain.entities.profile import Profile, Role

    repo = AsyncMock()
    uc = SubscriptionPlanUseCases(repo)
    customer = Profile(
        id="00000000-0000-0000-0000-000000000001", role=Role.customer,
        full_name="C", is_active=True, email=None, phone=None,
        phone_verified=False, avatar_url=None,
    )
    with pytest.raises(ForbiddenError):
        await uc.list_plans(customer)
    with pytest.raises(ForbiddenError):
        await uc.create_plan(customer, {})


@pytest.mark.asyncio
async def test_non_admin_cannot_manage_subscriptions():
    from unittest.mock import AsyncMock

    from app.application.use_cases.subscription import SalonSubscriptionUseCases
    from app.core.exceptions import ForbiddenError
    from app.domain.entities.profile import Profile, Role

    repo = AsyncMock()
    event_repo = AsyncMock()
    uc = SalonSubscriptionUseCases(repo, event_repo)
    owner = Profile(
        id="00000000-0000-0000-0000-000000000002", role=Role.owner,
        full_name="O", is_active=True, email=None, phone=None,
        phone_verified=False, avatar_url=None,
    )
    with pytest.raises(ForbiddenError):
        await uc.get_salon_subscription(owner, "salon1")
    with pytest.raises(ForbiddenError):
        await uc.create_test_subscription(owner, {})
    with pytest.raises(ForbiddenError):
        await uc.cancel_subscription(owner, "sub1")


@pytest.mark.asyncio
async def test_cannot_create_subscription_with_terminal_status():
    from unittest.mock import AsyncMock

    from app.application.use_cases.subscription import SalonSubscriptionUseCases
    from app.core.exceptions import ValidationError as AppValidationError
    from app.domain.entities.profile import Profile, Role

    repo = AsyncMock()
    event_repo = AsyncMock()
    uc = SalonSubscriptionUseCases(repo, event_repo)
    admin = Profile(
        id="00000000-0000-0000-0000-000000000003", role=Role.super_admin,
        full_name="A", is_active=True, email=None, phone=None,
        phone_verified=False, avatar_url=None,
    )
    with pytest.raises(AppValidationError):
        await uc.create_test_subscription(admin, {"status": "expired"})
    repo.create_subscription.assert_not_awaited()


# ── OpenAPI contract ─────────────────────────────────────────────────────────


def test_subscription_admin_endpoints_require_auth():
    from app.main import app

    paths = app.openapi()["paths"]
    admin_paths = [p for p in paths if "subscription" in p]
    assert len(admin_paths) >= 5
    for path in admin_paths:
        for method_info in paths[path].values():
            assert method_info.get("security"), f"{path} has no security"


def test_no_provider_fields_in_openapi():
    from app.main import app

    schema = app.openapi()
    raw = str(schema)
    assert "provider_customer_reference" not in raw
    assert "provider_subscription_reference" not in raw
