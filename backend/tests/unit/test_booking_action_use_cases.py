"""Unit tests for booking action requests and closure orchestration."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import BackgroundTasks

from app.api.v1.schemas.booking_actions import BookingActionRespondRequest
from app.application.use_cases.booking_actions import (
    BookingActionRequestUseCases,
    ClosureUseCases,
)
from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Role
from tests.conftest import make_mock_repo, make_owner, make_profile


@pytest.mark.asyncio
async def test_customer_creates_payment_confirmation_request() -> None:
    repo = make_mock_repo()
    repo.create_booking_action_request.return_value = {
        "id": "request-1",
        "_outbox_ids": ["outbox-1"],
    }
    use_cases = BookingActionRequestUseCases(repo)
    tasks = BackgroundTasks()

    result = await use_cases.create_customer_request(
        make_profile(), "booking-1", "payment_confirmation", None, tasks
    )

    assert result["id"] == "request-1"
    repo.create_booking_action_request.assert_awaited_once_with(
        "user-001",
        "booking-1",
        "payment_confirmation",
        None,
        cancellation_cutoff_minutes=settings.customer_cancellation_cutoff_minutes,
        allow_late_cancellation_requests=settings.allow_late_cancellation_requests,
    )
    assert len(tasks.tasks) == 1


@pytest.mark.asyncio
async def test_staff_cannot_create_customer_request() -> None:
    use_cases = BookingActionRequestUseCases(make_mock_repo())

    with pytest.raises(ForbiddenError):
        await use_cases.create_customer_request(
            make_profile(role=Role.staff),
            "booking-1",
            "cancellation",
            "Please cancel",
        )


@pytest.mark.asyncio
async def test_owner_lists_and_responds_to_requests() -> None:
    repo = make_mock_repo()
    repo.list_booking_action_requests.return_value = []
    repo.respond_booking_action_request.return_value = {
        "id": "request-1",
        "status": "resolved",
        "_outbox_ids": [],
    }
    use_cases = BookingActionRequestUseCases(repo)
    owner = make_owner()

    assert await use_cases.list_requests(owner, "pending") == []
    result = await use_cases.respond(
        owner, "request-1", "not_received", None
    )

    assert result["status"] == "resolved"
    repo.respond_booking_action_request.assert_awaited_once_with(
        owner.id, "request-1", "not_received", None
    )


def test_declined_cancellation_requires_reason() -> None:
    with pytest.raises(ValueError):
        BookingActionRespondRequest(decision="decline", reason="  ")


@pytest.mark.asyncio
async def test_closure_preview_and_apply_are_owner_only() -> None:
    repo = make_mock_repo()
    now = datetime.now(UTC)
    values = {
        "kind": "leave",
        "staff_id": "staff-1",
        "start_datetime": now,
        "end_datetime": now + timedelta(hours=2),
    }
    repo.preview_closure.return_value = [{"booking_id": "booking-1"}]
    repo.apply_closure.return_value = {
        "closure_id": "block-1",
        "affected_count": 1,
        "_outbox_ids": [],
    }
    use_cases = ClosureUseCases(repo)

    preview = await use_cases.preview(make_owner(), values)
    assert preview["affected_count"] == 1

    with pytest.raises(ForbiddenError):
        await use_cases.apply(
            make_profile(role=Role.staff),
            {**values, "reason": "Emergency", "affected_booking_ids": []},
        )



def test_http_pending_requests_for_owner_without_any_returns_empty_list(monkeypatch) -> None:
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient

    from app.api.deps import get_authenticated_session, get_current_actor
    from app.main import app

    repo = make_mock_repo()
    repo.list_booking_action_requests.return_value = []
    monkeypatch.setattr(
        "app.api.v1.routes.booking_actions._action_use_cases",
        lambda session: BookingActionRequestUseCases(repo),
    )

    async def session():
        yield AsyncMock()

    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_authenticated_session] = session
    try:
        response = TestClient(app).get("/v1/booking-action-requests?status=pending")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == []
    repo.list_booking_action_requests.assert_awaited_once_with(make_owner().id, "pending")
