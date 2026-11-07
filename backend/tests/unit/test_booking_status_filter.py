"""GET /v1/bookings accepts one or many statuses via commas or repeated parameters."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_mfa_checked_actor
from app.api.v1.routes.bookings import parse_booking_statuses
from app.application.use_cases.platform import BookingUseCases
from app.core.exceptions import ValidationError
from tests.conftest import make_booking, make_mock_repo, make_owner


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ([], None),
        (["confirmed"], ["confirmed"]),
        (["cancelled,rejected,no_show"], ["cancelled", "rejected", "no_show"]),
        (["cancelled", "rejected"], ["cancelled", "rejected"]),
        (["cancelled, rejected", "cancelled"], ["cancelled", "rejected"]),
        ([" ", ","], None),
    ],
)
def test_parse_booking_statuses(raw, expected):
    assert parse_booking_statuses(raw) == expected


@pytest.mark.parametrize("raw", [["bogus"], ["cancelled,bogus"], ["CANCELLED"]])
def test_parse_booking_statuses_rejects_unknown_values(raw):
    with pytest.raises(ValidationError, match="status"):
        parse_booking_statuses(raw)


def _get(monkeypatch, query: str):
    repo = make_mock_repo()
    repo.list_bookings.return_value = []
    monkeypatch.setattr(
        "app.api.v1.routes.bookings._use_cases", lambda session: BookingUseCases(repo)
    )

    async def session():
        yield AsyncMock()

    from app.main import app

    owner = make_owner()
    app.dependency_overrides[get_mfa_checked_actor] = lambda: owner
    app.dependency_overrides[get_authenticated_session] = session
    try:
        response = TestClient(app).get(f"/v1/bookings{query}")
    finally:
        app.dependency_overrides.clear()
    return response, repo, owner


@pytest.mark.parametrize(
    "query",
    ["?status=cancelled,rejected,no_show", "?status=cancelled&status=rejected&status=no_show"],
)
def test_http_accepts_comma_and_repeated_statuses(monkeypatch, query):
    response, repo, _ = _get(monkeypatch, query)

    assert response.status_code == 200
    assert repo.list_bookings.await_args.kwargs["booking_statuses"] == [
        "cancelled",
        "rejected",
        "no_show",
    ]


def test_http_without_status_passes_no_filter(monkeypatch):
    response, repo, _ = _get(monkeypatch, "")

    assert response.status_code == 200
    assert repo.list_bookings.await_args.kwargs["booking_statuses"] is None


def test_http_rejects_unknown_status(monkeypatch):
    response, repo, _ = _get(monkeypatch, "?status=cancelled,bogus")

    assert response.status_code == 422
    repo.list_bookings.assert_not_awaited()


def _post(monkeypatch, path: str):
    repo = make_mock_repo()
    repo.set_booking_archived.return_value = make_booking(status="cancelled")
    monkeypatch.setattr(
        "app.api.v1.routes.bookings._use_cases", lambda session: BookingUseCases(repo)
    )

    async def session():
        yield AsyncMock()

    from app.api.deps import get_current_actor
    from app.main import app

    owner = make_owner()
    app.dependency_overrides[get_current_actor] = lambda: owner
    app.dependency_overrides[get_authenticated_session] = session
    try:
        return TestClient(app).post(path), repo, owner
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(("action", "archived"), [("archive", True), ("unarchive", False)])
def test_http_archive_routes_call_the_use_case(monkeypatch, action, archived):
    booking_id = "11111111-1111-4111-8111-111111111111"

    response, repo, owner = _post(monkeypatch, f"/v1/bookings/{booking_id}/{action}")

    assert response.status_code == 200
    repo.set_booking_archived.assert_awaited_once_with(owner.id, booking_id, archived)


def test_http_archive_rejects_a_malformed_id(monkeypatch):
    response, repo, _ = _post(monkeypatch, "/v1/bookings/not-a-uuid/archive")

    assert response.status_code == 422
    repo.set_booking_archived.assert_not_awaited()
