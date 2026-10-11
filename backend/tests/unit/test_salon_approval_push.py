"""Owner push notification when an admin approves or rejects their salon."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.use_cases.admin import AdminUseCases
from app.core.config import Settings
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.push.fcm_gateway import FCMGateway
from tests.conftest import make_mock_repo, make_super_admin

MIGRATION = (
    Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0023_notification_data.py"
)


def _use_case(previous: str = "pending", previous_reason: str | None = None):
    repo = make_mock_repo()
    repo.admin_get_salon.return_value = {
        "id": "salon-001",
        "owner_id": "owner-001",
        "is_active": True,
        "profile_completed": True,
        "approval_status": previous,
        "rejection_reason": previous_reason,
    }
    notify = AsyncMock()
    return AdminUseCases(repo, AsyncMock(), notify_owner=notify), repo, notify


@pytest.mark.asyncio
async def test_approve_notifies_owner_with_status_payload():
    uc, _, notify = _use_case()
    await uc.approve_salon(make_super_admin(), "salon-001")
    notify.assert_awaited_once_with(
        user_id="owner-001",
        notification_type="approval_status",
        title="Your salon is verified 🎉",
        body="Customers can now discover and book your salon.",
        data={"type": "approval_status", "status": "approved"},
    )


@pytest.mark.asyncio
async def test_reject_notifies_owner_with_trimmed_reason():
    uc, _, notify = _use_case()
    await uc.reject_salon(make_super_admin(), "salon-001", "  Fix address  ")
    notify.assert_awaited_once_with(
        user_id="owner-001",
        notification_type="approval_status",
        title="Action needed on your salon",
        body="Our team left feedback. Open the app to review and resubmit.",
        data={"type": "approval_status", "status": "rejected", "reason": "Fix address"},
    )


@pytest.mark.asyncio
async def test_notification_failure_never_fails_the_decision():
    uc, repo, notify = _use_case()
    notify.side_effect = RuntimeError("fcm down")
    await uc.approve_salon(make_super_admin(), "salon-001")
    repo.admin_set_salon_approval.assert_awaited_once()


@pytest.mark.asyncio
async def test_repeated_approval_does_not_push_again():
    uc, _, notify = _use_case(previous="approved")
    await uc.approve_salon(make_super_admin(), "salon-001")
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeated_rejection_with_same_reason_is_silent_but_new_reason_pushes():
    uc, _, notify = _use_case(previous="rejected", previous_reason="Fix address")
    await uc.reject_salon(make_super_admin(), "salon-001", "Fix address")
    notify.assert_not_awaited()
    await uc.reject_salon(make_super_admin(), "salon-001", "Add photos")
    notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_notifier_configured_is_a_noop():
    repo = make_mock_repo()
    repo.admin_get_salon.return_value = {"is_active": True, "profile_completed": True}
    await AdminUseCases(repo, AsyncMock()).approve_salon(make_super_admin(), "salon-001")
    repo.admin_set_salon_approval.assert_awaited_once()


@pytest.mark.asyncio
async def test_enqueue_persists_data_json_and_allows_no_booking():
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value="outbox-1"))
    await PlatformRepository(session).enqueue_notification(
        user_id="owner-001",
        booking_id=None,
        notification_type="approval_status",
        title="t",
        body="b",
        data={"status": "approved"},
    )
    sql = str(session.execute.await_args.args[0])
    params = session.execute.await_args.args[1]
    assert ":data" in sql and "cast(:data as jsonb)" in sql
    assert params["booking_id"] is None
    assert json.loads(params["data"]) == {"status": "approved"}


def test_provider_data_merges_notification_data_as_strings():
    gateway = FCMGateway(Settings(), AsyncMock())
    payload = gateway._provider_data(
        {
            "id": "n1",
            "booking_id": None,
            "type": "approval_status",
            "data": {"type": "approval_status", "status": "rejected", "reason": "Fix address"},
        }
    )
    assert payload["status"] == "rejected"
    assert payload["reason"] == "Fix address"
    assert payload["type"] == "approval_status"
    assert payload["notification_id"] == "n1"
    assert "booking_id" not in payload


def test_provider_data_still_works_for_notifications_without_data():
    gateway = FCMGateway(Settings(), AsyncMock())
    assert gateway._provider_data({"id": "n1", "booking_id": "b1", "type": "x"}) == {
        "notification_id": "n1",
        "booking_id": "b1",
        "type": "x",
    }


def test_provider_data_ignores_non_object_notification_data():
    gateway = FCMGateway(Settings(), AsyncMock())
    assert gateway._provider_data({"id": "n1", "type": "x", "data": "[1, 2]"}) == {
        "notification_id": "n1",
        "type": "x",
    }


@pytest.mark.asyncio
async def test_admin_route_notifier_enqueues_without_booking_and_forwards_data():
    from app.api.v1.routes import admin as admin_routes

    with patch.object(admin_routes, "enqueue_and_deliver_notification", AsyncMock()) as enqueue:
        await admin_routes._notify_owner(
            user_id="owner-001",
            notification_type="approval_status",
            title="t",
            body="b",
            data={"status": "approved"},
        )
    enqueue.assert_awaited_once_with(
        user_id="owner-001",
        booking_id=None,
        notification_type="approval_status",
        title="t",
        body="b",
        data={"status": "approved"},
    )


def _migration():
    spec = importlib.util.spec_from_file_location("m0023", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_adds_and_drops_nullable_data_column_one_statement_each():
    module = _migration()
    assert module.revision == "0023_notification_data"
    assert module.down_revision == "0022_salon_accepting_bookings"
    for direction, expected in [("upgrade", "add column"), ("downgrade", "drop column")]:
        statements: list[str] = []
        with patch.object(module.op, "execute", side_effect=statements.append):
            getattr(module, direction)()
        assert len(statements) == 1
        assert expected in statements[0].lower() and "notifications" in statements[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["approve", "reject"])
async def test_push_is_deferred_to_background_tasks_so_admin_request_never_waits(decision):
    from fastapi import BackgroundTasks

    uc, repo, notify = _use_case()
    tasks = BackgroundTasks()
    args = ("Fix address",) if decision == "reject" else ()
    await getattr(uc, f"{decision}_salon")(make_super_admin(), "salon-001", *args, tasks)
    repo.admin_set_salon_approval.assert_awaited_once()
    notify.assert_not_awaited()  # nothing sent while the request is still being handled
    await tasks()
    notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_background_push_failure_is_swallowed():
    from fastapi import BackgroundTasks

    uc, _, notify = _use_case()
    notify.side_effect = RuntimeError("expo timeout")
    tasks = BackgroundTasks()
    await uc.approve_salon(make_super_admin(), "salon-001", tasks)
    await tasks()  # must not raise
    notify.assert_awaited_once()


def test_admin_routes_hand_a_background_task_runner_to_the_use_case():
    from unittest.mock import MagicMock

    from fastapi.testclient import TestClient

    from app.api.deps import get_auth_admin_gateway, get_authenticated_session, get_current_actor
    from app.main import app

    salon = {
        "id": "s", "owner_id": "o", "name": "Salon", "timezone": "UTC", "approval_mode": "auto",
        "profile_completed": True, "is_active": True, "approval_status": "approved",
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
    }
    uc = MagicMock()
    uc.approve_salon = AsyncMock(return_value=salon)
    uc.reject_salon = AsyncMock(return_value=salon)

    async def session():
        yield object()

    app.dependency_overrides[get_current_actor] = lambda: make_super_admin()
    app.dependency_overrides[get_authenticated_session] = session
    app.dependency_overrides[get_auth_admin_gateway] = lambda: object()
    salon_id = "00000000-0000-0000-0000-000000000001"
    try:
        with patch("app.api.v1.routes.admin._admin_use_cases", lambda s, a: uc):
            client = TestClient(app)
            approved = client.post(f"/v1/admin/salons/{salon_id}/approve")
            rejected = client.post(
                f"/v1/admin/salons/{salon_id}/reject", json={"rejection_reason": "Fix"}
            )
    finally:
        app.dependency_overrides.clear()
    from fastapi import BackgroundTasks

    assert approved.status_code == rejected.status_code == 200
    assert isinstance(uc.approve_salon.await_args.args[-1], BackgroundTasks)
    assert isinstance(uc.reject_salon.await_args.args[-1], BackgroundTasks)
