"""salons.accepting_bookings: owner toggle, public payloads, and 409 mapping.

DB-level enforcement (get_available_slots / create_booking) lives in migration 0022 and is
asserted here against the migration SQL; behaviour against a live Postgres is covered by the
opt-in isolated-schema test in tests/integration.
"""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_authenticated_session,
    get_cache,
    get_current_actor,
    get_session,
)
from app.api.v1.schemas.platform import (
    OwnerSalonResponse,
    OwnerSalonSettingsRequest,
    SalonDetailResponse,
    SalonSummaryResponse,
)
from app.api.v1.schemas.walkin import WalkInSalonResponse
from app.application.use_cases.platform import OwnerUseCases
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    SalonApprovalRequiredError,
    SalonNotAcceptingBookingsError,
)
from app.domain.entities.profile import Role
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.main import app
from tests.conftest import make_mock_repo, make_owner, make_profile
from tests.unit.test_cache_integration import InMemoryCache

MIGRATION = (
    Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0022_salon_accepting_bookings.py"
)
SALON_ID = "00000000-0000-0000-0000-000000000001"


def _owner_salon(accepting: bool) -> dict:
    return {
        "id": SALON_ID, "owner_id": "owner-001", "name": "Salon", "timezone": "UTC",
        "working_hours": {}, "approval_mode": "auto", "slot_interval_minutes": 30,
        "qr_token": "qr-abc", "profile_completed": True, "approval_status": "approved",
        "is_active": True, "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z", "accepting_bookings": accepting,
    }


# ── schemas ──────────────────────────────────────────────────────────────────


def test_settings_request_accepts_accepting_bookings_and_dumps_only_set_fields():
    assert OwnerSalonSettingsRequest(accepting_bookings=False).model_dump(exclude_unset=True) == {
        "accepting_bookings": False
    }
    assert OwnerSalonSettingsRequest().model_dump(exclude_unset=True) == {}


def test_owner_response_exposes_accepting_bookings():
    assert OwnerSalonResponse(**_owner_salon(False)).accepting_bookings is False


def test_public_payloads_include_accepting_bookings_defaulting_true():
    assert "accepting_bookings" in SalonSummaryResponse.model_fields
    assert "accepting_bookings" in SalonDetailResponse.model_fields
    walkin = WalkInSalonResponse(
        id="s", name="n", timezone="UTC", approval_mode="auto", accepting_bookings=False
    )
    assert walkin.accepting_bookings is False
    # Payloads cached before the deploy lack the key and must read as "accepting".
    assert WalkInSalonResponse(id="s", name="n", timezone="UTC", approval_mode="auto").accepting_bookings


# ── use case authorization ───────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.customer, Role.staff, Role.super_admin])
async def test_non_owner_cannot_toggle(role):
    repo = make_mock_repo()
    with pytest.raises(ForbiddenError):
        await OwnerUseCases(repo).update_settings(
            make_profile(role=role), {"accepting_bookings": False}
        )
    repo.update_owner_salon.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("approval_status", ["pending", "rejected"])
async def test_unapproved_salon_cannot_toggle(approval_status):
    repo = make_mock_repo()
    repo.get_workspace_salon.return_value["approval_status"] = approval_status
    with pytest.raises(SalonApprovalRequiredError):
        await OwnerUseCases(repo).update_settings(make_owner(), {"accepting_bookings": False})
    repo.update_owner_salon.assert_not_awaited()


@pytest.mark.asyncio
async def test_unapproved_owner_can_still_edit_other_settings():
    repo = make_mock_repo()
    repo.get_workspace_salon.return_value["approval_status"] = "pending"
    await OwnerUseCases(repo).update_settings(make_owner(), {"approval_mode": "manual"})
    repo.update_owner_salon.assert_awaited_once_with("owner-001", {"approval_mode": "manual"})


@pytest.mark.asyncio
async def test_toggle_only_writes_the_flag_and_leaves_existing_bookings_alone():
    repo = make_mock_repo()
    repo.update_owner_salon.return_value = _owner_salon(False)
    await OwnerUseCases(repo).update_settings(make_owner(), {"accepting_bookings": False})
    repo.update_owner_salon.assert_awaited_once_with("owner-001", {"accepting_bookings": False})
    for untouched in ("update_booking_status", "apply_closure", "cancel_customer_booking",
                      "create_notification", "respond_booking_action_request"):
        getattr(repo, untouched).assert_not_awaited()


# ── HTTP: settings endpoint + cache invalidation ─────────────────────────────


@pytest.fixture
def client():
    async def session():
        yield AsyncMock()

    app.dependency_overrides[get_authenticated_session] = session
    app.dependency_overrides[get_session] = session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("accepting", [False, True])
def test_patch_settings_toggles_and_invalidates_salon_and_walkin_cache(client, accepting):
    repo = make_mock_repo()
    repo.update_owner_salon.return_value = _owner_salon(accepting)
    cache = InMemoryCache()
    cache._store.update({
        f"salon:{SALON_ID}:detail": {"stale": 1}, f"salon:{SALON_ID}:services": [],
        "walkin:qr:qr-abc": {"stale": 1}, "salon:other:detail": {"keep": 1},
    })
    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_cache] = lambda: cache
    with patch("app.api.v1.routes.owner._use_cases", lambda s: OwnerUseCases(repo)):
        response = client.patch("/v1/salons/me/settings", json={"accepting_bookings": accepting})
    assert response.status_code == 200
    assert response.json()["accepting_bookings"] is accepting
    assert set(cache._store) == {"salon:other:detail"}


def test_patch_settings_forbidden_for_customer_and_pending_salon(client):
    repo = make_mock_repo()
    app.dependency_overrides[get_cache] = lambda: InMemoryCache()
    with patch("app.api.v1.routes.owner._use_cases", lambda s: OwnerUseCases(repo)):
        app.dependency_overrides[get_current_actor] = lambda: make_profile(role=Role.customer)
        assert client.patch("/v1/salons/me/settings", json={"accepting_bookings": False}).status_code == 403
        repo.get_workspace_salon.return_value["approval_status"] = "pending"
        app.dependency_overrides[get_current_actor] = lambda: make_owner()
        response = client.patch("/v1/salons/me/settings", json={"accepting_bookings": False})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "awaiting_admin_approval"
    repo.update_owner_salon.assert_not_awaited()


def test_patch_settings_rejects_non_boolean(client):
    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_cache] = lambda: InMemoryCache()
    response = client.patch("/v1/salons/me/settings", json={"accepting_bookings": "maybe"})
    assert response.status_code == 422


# ── HTTP: booking creation returns the distinct 409 ──────────────────────────


def test_post_booking_returns_distinct_409_when_not_accepting(client):
    uc = AsyncMock()
    uc.create_booking.side_effect = SalonNotAcceptingBookingsError("Salon is not accepting bookings")
    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=Role.customer)
    app.dependency_overrides[get_cache] = lambda: InMemoryCache()
    payload = {
        "salon_id": SALON_ID, "staff_id": "00000000-0000-0000-0000-000000000002",
        "service_ids": ["00000000-0000-0000-0000-000000000003"],
        "start_datetime": "2030-01-01T10:00:00Z", "customer_name": "Alice",
    }
    with patch("app.api.v1.routes.bookings._use_cases", return_value=uc):
        response = client.post("/v1/bookings", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "salon_not_accepting_bookings"
    assert issubclass(SalonNotAcceptingBookingsError, ConflictError)


def test_walkin_qr_booking_returns_same_409(client):
    repo = MagicMock()
    repo.validate_qr_token = AsyncMock(return_value=SALON_ID)
    repo.create_booking = AsyncMock(side_effect=SalonNotAcceptingBookingsError("closed"))
    app.dependency_overrides[get_current_actor] = lambda: make_profile(role=Role.customer)
    app.dependency_overrides[get_cache] = lambda: InMemoryCache()
    payload = {
        "salon_id": SALON_ID, "staff_id": "00000000-0000-0000-0000-000000000002",
        "service_ids": ["00000000-0000-0000-0000-000000000003"],
        "start_datetime": "2030-01-01T10:00:00Z", "customer_name": "Alice",
    }
    with patch("app.api.v1.routes.walkin.PlatformRepository", return_value=repo):
        response = client.post("/v1/walkin/qr-abc/bookings", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "salon_not_accepting_bookings"


# ── repository: DB error mapping ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_repository_maps_db_error_to_distinct_error_before_generic_slot_match():
    session = AsyncMock()
    session.execute.side_effect = Exception("salon_not_accepting_bookings")
    values = {
        "salon_id": SALON_ID, "staff_id": "s", "service_ids": [], "start_datetime": None,
        "customer_name": "A", "customer_phone": None, "source": "manual_walkin", "notes": None,
    }
    with pytest.raises(SalonNotAcceptingBookingsError) as exc:
        await PlatformRepository(session).create_booking(values)
    assert exc.value.code == "salon_not_accepting_bookings"
    assert exc.value.status_code == 409
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_repository_still_maps_slot_errors_as_before():
    session = AsyncMock()
    session.execute.side_effect = Exception("Selected slot is no longer available")
    values = {"salon_id": SALON_ID, "staff_id": "s", "service_ids": [], "start_datetime": None,
              "customer_name": "A", "customer_phone": None, "source": "app", "notes": None}
    with pytest.raises(ConflictError) as exc:
        await PlatformRepository(session).create_booking(values)
    assert exc.value.code == "slot_unavailable"


# ── migration SQL ────────────────────────────────────────────────────────────


def _migration_statements(direction: str) -> list[str]:
    spec = importlib.util.spec_from_file_location("m0022", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    statements: list[str] = []
    with patch.object(module.op, "execute", side_effect=statements.append):
        getattr(module, direction)()
    return statements


def test_migration_adds_column_and_gates_both_db_functions():
    sql = _migration_statements("upgrade")
    joined = "\n".join(sql).lower()
    assert "add column accepting_bookings boolean not null default true" in joined
    slots = next(s for s in sql if "function get_available_slots" in s)
    booking = next(s for s in sql if "function create_booking" in s)
    assert "sl.accepting_bookings" in slots
    assert "salon_not_accepting_bookings" in booking
    # Every statement runs on its own (asyncpg rejects multi-statement prepared SQL).
    assert len(sql) == 3 and "function" not in sql[0].lower()
    # Toggling never cancels or notifies: the migration touches no booking/notification rows.
    assert "update bookings" not in joined and "notifications" not in joined
    # Manual walk-ins are blocked too, so the guard must not be limited to p_source = 'app'.
    guard = booking[booking.index("if not v_accepting"): booking.index("end if;", booking.index("if not v_accepting"))]
    assert "p_source" not in guard


def test_migration_downgrade_restores_functions_then_drops_column():
    sql = _migration_statements("downgrade")
    assert "accepting_bookings" not in "\n".join(s for s in sql if "function" in s)
    assert "drop column accepting_bookings" in sql[-1].lower()
