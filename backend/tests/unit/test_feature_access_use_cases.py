"""Super-admin feature access: who may change it, what it validates, and how finance honours it."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_current_actor
from app.application.use_cases.feature_access import FeatureAccessUseCases
from app.application.use_cases.finance import FinanceUseCases
from app.core.exceptions import EntitlementRequiredError, ForbiddenError, ValidationError
from app.domain.entities.profile import Role
from app.main import app
from tests.conftest import make_profile, make_super_admin

SALON = "11111111-1111-4111-8111-111111111111"
NOW = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)


def store() -> AsyncMock:
    repo = AsyncMock()
    repo.catalog.return_value = [{"key": "split_bill", "label": "Staff split bill", "description": "", "sort_order": 10}]
    repo.matrix.return_value = {"split_bill": {"trial": True, "growth": False, "premium": True}}
    repo.plan_content.return_value = {}
    repo.list_overrides.return_value = []
    return repo


@pytest.mark.parametrize("role", [Role.owner, Role.customer, Role.staff])
async def test_only_a_super_admin_can_read_or_change_feature_access(role):
    repo = store()
    uc = FeatureAccessUseCases(repo)
    actor = make_profile(role=role)
    calls = [
        uc.overview(actor),
        uc.save_matrix(actor, [{"feature_key": "split_bill", "audience": "growth", "enabled": True}]),
        uc.update_feature(actor, "split_bill", "Split", ""),
        uc.save_plan_content(actor, "growth", "h", "d", []),
        uc.set_override(actor, SALON, "split_bill", True, None, None),
        uc.clear_override(actor, SALON, "split_bill"),
    ]
    for call in calls:
        with pytest.raises(ForbiddenError):
            await call
    repo.save_matrix.assert_not_awaited()
    repo.set_override.assert_not_awaited()


async def test_overview_lays_the_matrix_out_per_audience():
    overview = await FeatureAccessUseCases(store()).overview(make_super_admin())
    assert overview["features"][0]["access"] == {"trial": True, "growth": False, "premium": True}


async def test_saving_the_matrix_records_who_did_it():
    repo = store()
    cells = [{"feature_key": "split_bill", "audience": "growth", "enabled": True}]
    await FeatureAccessUseCases(repo).save_matrix(make_super_admin(), cells)
    repo.save_matrix.assert_awaited_once_with(cells, "admin-001")


async def test_blank_feature_name_and_blank_plan_bullets_are_cleaned_or_refused():
    repo = store()
    uc = FeatureAccessUseCases(repo)
    with pytest.raises(ValidationError):
        await uc.update_feature(make_super_admin(), "split_bill", "   ", "")
    await uc.save_plan_content(make_super_admin(), "premium", " Grow ", " More ", [" a ", "", "  "])
    repo.save_plan_content.assert_awaited_once_with("premium", "Grow", "More", ["a"])


async def test_override_end_date_must_be_in_the_future_and_carry_a_time_zone():
    uc = FeatureAccessUseCases(store(), clock=lambda: NOW)
    admin = make_super_admin()
    with pytest.raises(ValidationError):
        await uc.set_override(admin, SALON, "split_bill", True, NOW - timedelta(days=1), None)
    with pytest.raises(ValidationError):
        await uc.set_override(admin, SALON, "split_bill", True, datetime(2026, 12, 1), None)
    await uc.set_override(admin, SALON, "split_bill", True, NOW + timedelta(days=3), "  trial extension ")
    assert uc.repository.set_override.await_args.args[-2:] == ("trial extension", "admin-001")


async def test_override_without_an_end_date_is_allowed():
    repo = store()
    await FeatureAccessUseCases(repo, clock=lambda: NOW).set_override(make_super_admin(), SALON, "split_bill", False, None, None)
    repo.set_override.assert_awaited_once()


@pytest.mark.parametrize("method,path", [("GET", "/v1/admin/features"), ("PUT", "/v1/admin/features/access")])
@pytest.mark.parametrize("role", [Role.owner, Role.customer, Role.staff])
def test_feature_routes_reject_other_roles_before_the_database(method, path, role):
    async def session():
        yield None

    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=role)
    app.dependency_overrides[get_authenticated_session] = session
    try:
        response = TestClient(app).request(
            method, path, json={"cells": [{"feature_key": "split_bill", "audience": "growth", "enabled": True}]}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


def test_matrix_payload_rejects_unknown_audiences_and_extra_fields():
    async def session():
        yield None

    app.dependency_overrides[get_current_actor] = lambda: make_super_admin()
    app.dependency_overrides[get_authenticated_session] = session
    try:
        client = TestClient(app)
        bad_audience = client.put("/v1/admin/features/access", json={"cells": [{"feature_key": "split_bill", "audience": "gold", "enabled": True}]})
        extra = client.put("/v1/admin/features/access", json={"cells": [], "other": 1})
        bad_key = client.put(f"/v1/admin/salons/{SALON}/feature-overrides/Bad-Key", json={"enabled": True})
    finally:
        app.dependency_overrides.clear()
    assert bad_audience.status_code == extra.status_code == bad_key.status_code == 422


# --- finance honours the switches ---------------------------------------------------------------


class FinanceRepo:
    def __init__(self, feature_access):
        self.feature_access = feature_access

    async def owner_salon(self, _owner_id):
        return {"id": SALON, "is_active": True, "profile_completed": True, "approval_status": "approved"}

    async def plan_access(self, _salon_id, _now):
        return {"features": {}, "entitlement_active": True, "trial": None, "feature_access": self.feature_access}


def on(*keys, source="plan"):
    return {k: {"enabled": True, "source": source, "plans": ["premium"]} for k in keys}


def off(*keys):
    return {k: {"enabled": False, "source": "plan", "plans": ["premium"]} for k in keys}


async def test_a_locked_feature_is_refused_for_reads_and_writes():
    uc = FinanceUseCases(FinanceRepo({**on("finance_page"), **off("daily_ledger")}), clock=lambda: NOW)
    with pytest.raises(EntitlementRequiredError):
        await uc._salon(make_profile(role=Role.owner))
    with pytest.raises(EntitlementRequiredError):
        await uc._salon(make_profile(role=Role.owner), write=True)


async def test_a_locked_finance_page_locks_every_tab_even_if_the_tab_is_unlocked():
    uc = FinanceUseCases(FinanceRepo({**off("finance_page"), **on("daily_ledger")}), clock=lambda: NOW)
    with pytest.raises(EntitlementRequiredError):
        await uc._salon(make_profile(role=Role.owner))


async def test_an_unlocked_feature_can_read_and_write():
    uc = FinanceUseCases(FinanceRepo(on("finance_page", "daily_ledger")), clock=lambda: NOW)
    salon = await uc._salon(make_profile(role=Role.owner), write=True)
    assert salon["can_write"] is True


async def test_a_salon_with_no_live_plan_or_trial_keeps_read_only_access():
    none = {"daily_ledger": {"enabled": False, "source": "none", "plans": []}, "finance_page": {"enabled": False, "source": "none", "plans": []}}
    uc = FinanceUseCases(FinanceRepo(none), clock=lambda: NOW)
    assert (await uc._salon(make_profile(role=Role.owner)))["can_write"] is False
    with pytest.raises(EntitlementRequiredError):
        await uc._salon(make_profile(role=Role.owner), write=True)


async def test_an_older_repository_without_switches_keeps_the_previous_plan_rule():
    class Old(FinanceRepo):
        async def plan_access(self, _salon_id, _now):
            return {"features": {"daily_ledger": True}, "entitlement_active": True, "trial": None}

    salon = await FinanceUseCases(Old(None), clock=lambda: NOW)._salon(make_profile(role=Role.owner), write=True)
    assert salon["can_write"] is True
