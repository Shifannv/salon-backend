"""Public discovery ranking and the admin display_priority contract."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.admin import AdminSalonResponse, AdminUpdateSalonRequest
from app.domain.entities.profile import Role
from app.main import app
from tests.unit.test_public_salon_visibility import public_api  # noqa: F401


def add_salon(session, key, name, *, priority=0, lat=None, lng=None,
              status="approved", active=True, complete=True):
    salon_id = f"00000000-0000-0000-0000-{key:012d}"
    session.db.execute(
        "insert into salons (id,name,timezone,working_hours,approval_mode,slot_interval_minutes,"
        "approval_status,is_active,profile_completed,display_priority,lat,lng) "
        "values (?,?, 'UTC','{}','automatic',30,?,?,?,?,?,?)",
        (salon_id, name, status, active, complete, priority, lat, lng),
    )
    return salon_id


@pytest.fixture
def ranked(public_api):  # noqa: F811
    client, session, _ = public_api
    session.db.execute("delete from salons")
    return client, session


def ids(response):
    assert response.status_code == 200
    return [row["id"] for row in response.json()]


def test_higher_priority_first_then_distance_then_name_then_id(ranked):
    client, session = ranked
    far_vip = add_salon(session, 1, "Zed", priority=10, lat=13.5, lng=80)
    near_vip = add_salon(session, 2, "Yak", priority=10, lat=13.0, lng=80)
    tie_b = add_salon(session, 3, "Bravo", priority=5, lat=13.1, lng=80)
    tie_a = add_salon(session, 4, "Alpha", priority=5, lat=13.1, lng=80)
    same_name_hi = add_salon(session, 6, "Clone", priority=5, lat=13.1, lng=80)
    same_name_lo = add_salon(session, 5, "Clone", priority=5, lat=13.1, lng=80)
    plain = add_salon(session, 7, "Plain", priority=0, lat=13.0, lng=80)
    assert ids(client.get("/v1/salons?lat=13&lng=80")) == [
        near_vip, far_vip, tie_a, tie_b, same_name_lo, same_name_hi, plain,
    ]
    assert ids(client.get("/v1/salons/nearby?latitude=13&longitude=80")) == [
        near_vip, far_vip, tie_a, tie_b, same_name_lo, same_name_hi, plain,
    ]


def test_missing_coordinates_sort_after_known_distance_within_priority(ranked):
    client, session = ranked
    unknown = add_salon(session, 1, "Aardvark", priority=3)
    known = add_salon(session, 2, "Zulu", priority=3, lat=13.0, lng=80)
    assert ids(client.get("/v1/salons?lat=13&lng=80")) == [known, unknown]
    assert ids(client.get("/v1/salons")) == [unknown, known]


def test_ordering_happens_before_pagination(ranked):
    client, session = ranked
    low = [add_salon(session, n, f"Low{n}", priority=0) for n in range(1, 4)]
    top = add_salon(session, 9, "Zzz", priority=99)
    assert ids(client.get("/v1/salons?limit=1")) == [top]
    assert ids(client.get("/v1/salons?limit=2&offset=1")) == low[:2]


def test_hidden_salons_never_appear_even_with_top_priority(ranked):
    client, session = ranked
    shown = add_salon(session, 1, "Shown", priority=0)
    add_salon(session, 2, "Pending", priority=1000, status="pending")
    add_salon(session, 3, "Rejected", priority=1000, status="rejected")
    add_salon(session, 4, "Inactive", priority=1000, active=False)
    add_salon(session, 5, "Incomplete", priority=1000, complete=False)
    for path in ("/v1/salons", "/v1/salons?search=Sh", "/v1/salons/nearby?lat=1&lng=1"):
        assert ids(client.get(path)) == [shown]


def test_priority_change_affects_next_response_and_is_not_public(ranked):
    client, session = ranked
    first = add_salon(session, 1, "Alpha")
    second = add_salon(session, 2, "Beta")
    assert ids(client.get("/v1/salons")) == [first, second]
    session.db.execute("update salons set display_priority=7 where id=?", (second,))
    response = client.get("/v1/salons")
    assert ids(response) == [second, first]
    assert all("display_priority" not in row for row in response.json())


def test_admin_request_validates_priority():
    assert AdminUpdateSalonRequest(display_priority=0).display_priority == 0
    assert AdminUpdateSalonRequest().display_priority is None
    for bad in (-1, 100001, 1.5, "5", True):
        with pytest.raises(ValidationError):
            AdminUpdateSalonRequest(display_priority=bad)


def test_admin_response_exposes_priority_and_audit_actor():
    assert "display_priority" in AdminSalonResponse.model_fields
    assert "updated_by" in AdminSalonResponse.model_fields


def _actor(role):
    from app.domain.entities.profile import Profile

    return Profile(
        id="11111111-1111-1111-1111-111111111111", role=role, full_name="T", is_active=True,
        email=None, phone=None, phone_verified=False, avatar_url=None,
    )


@pytest.mark.parametrize("role", [Role.owner, Role.customer])
def test_non_admin_cannot_patch_display_priority(role):
    overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_actor] = lambda: _actor(role)
    app.dependency_overrides[get_authenticated_session] = lambda: None
    try:
        response = TestClient(app).patch(
            "/v1/admin/salons/00000000-0000-0000-0000-000000000001",
            json={"display_priority": 50},
        )
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)


@pytest.mark.asyncio
async def test_use_case_passes_priority_for_super_admin_only():
    from unittest.mock import AsyncMock

    from app.application.use_cases.admin import AdminUseCases
    from app.core.exceptions import ForbiddenError

    repo = AsyncMock()
    repo.admin_update_salon.return_value = {"display_priority": 9}
    use_cases = AdminUseCases(repo, AsyncMock())
    result = await use_cases.update_salon(_actor(Role.super_admin), "s1", {"display_priority": 9})
    assert result == {"display_priority": 9}
    repo.admin_update_salon.assert_awaited_once_with("s1", {"display_priority": 9})
    for role in (Role.owner, Role.customer):
        with pytest.raises(ForbiddenError):
            await use_cases.update_salon(_actor(role), "s1", {"display_priority": 9})


# ── Subscription promotion ranking ──────────────────────────────────────────


def _subscribe(session, salon_id, *, weight=10, status="active"):
    plan_id = f"plan-{weight}"
    session.db.execute(
        "insert or ignore into subscription_plans (id, code, name, tier, ranking_weight, is_active) "
        "values (?, ?, ?, 0, ?, 1)",
        (plan_id, plan_id, f"Plan {weight}", weight),
    )
    session.db.execute(
        "insert into salon_subscriptions (id, salon_id, plan_id, status, "
        "current_period_start, current_period_end) "
        "values (?, ?, ?, ?, '2020-01-01', '2099-01-01')",
        (f"sub-{salon_id}", salon_id, plan_id, status),
    )


def test_subscription_weight_ranks_above_display_priority(ranked):
    client, session = ranked
    high_priority = add_salon(session, 1, "HighPri", priority=100)
    subscribed = add_salon(session, 2, "Subscribed", priority=0)
    _subscribe(session, subscribed, weight=50)
    assert ids(client.get("/v1/salons")) == [subscribed, high_priority]


def test_inactive_subscription_does_not_boost(ranked):
    client, session = ranked
    base = add_salon(session, 1, "Base", priority=5)
    sub_salon = add_salon(session, 2, "SubSalon", priority=0)
    _subscribe(session, sub_salon, weight=100, status="expired")
    assert ids(client.get("/v1/salons")) == [base, sub_salon]


def test_no_subscription_fields_in_public_response(ranked):
    client, session = ranked
    s = add_salon(session, 1, "S1")
    _subscribe(session, s, weight=50)
    response = client.get("/v1/salons")
    assert response.status_code == 200
    row = response.json()[0]
    for field in ("ranking_weight", "subscription_status", "plan_code", "plan_tier"):
        assert field not in row
