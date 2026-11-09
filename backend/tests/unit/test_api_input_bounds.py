"""Input bounds, UUID ids and paging on the API boundary (schemas and routes)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.routes import booking_actions, bookings, notifications
from app.api.v1.schemas.booking_actions import (
    BookingActionRequestResponse,
    ClosureApplyRequest,
    ClosurePreviewRequest,
)
from app.api.v1.schemas.platform import (
    BlockedSlotCreateRequest,
    BookingCreateRequest,
    HolidayCreateRequest,
    ServiceCreateRequest,
    ServiceUpdateRequest,
    StaffServiceAssignRequest,
)
from app.application.use_cases.notification_use_cases import NotificationUseCases
from app.core.exceptions import register_exception_handlers
from tests.conftest import make_owner

UPPER = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
LOWER = UPPER.lower()
NOW = datetime(2030, 1, 1, 10, tzinfo=UTC)


def _client(router):
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    register_exception_handlers(app)
    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_authenticated_session] = lambda: Mock()
    return TestClient(app, raise_server_exceptions=False)


def _booking(**over):
    base = {
        "salon_id": LOWER, "staff_id": LOWER, "service_ids": [LOWER],
        "start_datetime": NOW.isoformat(), "customer_name": "A",
    }
    return {**base, **over}


# -- a. UUID ids ---------------------------------------------------------------


def test_booking_create_normalises_uuids_and_dumps_strings():
    dumped = BookingCreateRequest(**_booking(salon_id=UPPER, service_ids=[UPPER])).model_dump()
    assert dumped["salon_id"] == LOWER
    assert dumped["service_ids"] == [LOWER]
    assert isinstance(dumped["staff_id"], str)


@pytest.mark.parametrize("over", [
    {"salon_id": "not-a-uuid"}, {"staff_id": "not-a-uuid"}, {"service_ids": ["nope"]},
])
def test_booking_create_rejects_malformed_ids(over):
    with pytest.raises(ValidationError):
        BookingCreateRequest(**_booking(**over))


def test_closure_requests_validate_uuid_ids():
    leave = {"kind": "leave", "start_datetime": NOW, "end_datetime": NOW + timedelta(hours=1)}
    with pytest.raises(ValidationError):
        ClosurePreviewRequest(**leave, staff_id="bad")
    assert ClosurePreviewRequest(**leave, staff_id=UPPER).model_dump()["staff_id"] == LOWER
    applied = ClosureApplyRequest(**leave, reason="x", affected_booking_ids=[UPPER])
    assert applied.model_dump()["affected_booking_ids"] == [LOWER]
    with pytest.raises(ValidationError):
        ClosureApplyRequest(**leave, reason="x", affected_booking_ids=["bad"])


def test_blocked_slot_staff_id_is_uuid():
    kw = {"start_datetime": NOW, "end_datetime": NOW + timedelta(hours=1)}
    with pytest.raises(ValidationError):
        BlockedSlotCreateRequest(staff_id="bad", **kw)
    assert BlockedSlotCreateRequest(staff_id=UPPER, **kw).model_dump()["staff_id"] == LOWER
    assert BlockedSlotCreateRequest(**kw).model_dump()["staff_id"] is None


def test_malformed_booking_id_is_422_not_500():
    client = _client(bookings.router)
    assert client.get("/v1/bookings/not-a-uuid").status_code == 422
    assert client.post("/v1/bookings/not-a-uuid/approve").status_code == 422


def test_malformed_notification_id_is_422():
    assert _client(notifications.router).post("/v1/notifications/nope/read").status_code == 422


def test_malformed_request_id_is_422():
    client = _client(booking_actions.router)
    response = client.post("/v1/booking-action-requests/nope/respond", json={"decision": "approve"})
    assert response.status_code == 422


def test_route_hands_use_case_a_lowercase_string_id():
    use_cases = SimpleNamespace(get_booking=AsyncMock(side_effect=RuntimeError("stop")))
    with patch.object(bookings, "_use_cases", lambda session: use_cases):
        _client(bookings.router).get(f"/v1/bookings/{UPPER}")
    assert use_cases.get_booking.await_args.args[1] == LOWER


# -- b. blocked slot datetimes -------------------------------------------------


def test_blocked_slot_requires_timezone_aware_datetimes():
    with pytest.raises(ValidationError):
        BlockedSlotCreateRequest(start_datetime=datetime(2030, 1, 1, 10), end_datetime=NOW)
    with pytest.raises(ValidationError):
        BlockedSlotCreateRequest(start_datetime=NOW, end_datetime=datetime(2030, 1, 1, 12))


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(hours=-1)])
def test_blocked_slot_end_must_follow_start(delta):
    with pytest.raises(ValidationError, match="end_datetime must be later than start_datetime"):
        BlockedSlotCreateRequest(start_datetime=NOW, end_datetime=NOW + delta)


# -- c. money, duration and text bounds ----------------------------------------


def test_service_price_bounds():
    ok = ServiceCreateRequest(name="Cut", duration_minutes=30, price=Decimal("99999999.99"))
    assert ok.price == Decimal("99999999.99")
    for bad in ("100000000.00", "10.123", "NaN", "Infinity", "-1"):
        with pytest.raises(ValidationError):
            ServiceCreateRequest(name="Cut", duration_minutes=30, price=bad)
    with pytest.raises(ValidationError):
        ServiceUpdateRequest(price="1.005")
    with pytest.raises(ValidationError):
        StaffServiceAssignRequest(service_id="s", price_override="NaN")


def test_duration_upper_bound_is_a_day():
    assert ServiceCreateRequest(name="Cut", duration_minutes=1440, price=1).duration_minutes == 1440
    for model, kw in (
        (ServiceCreateRequest, {"name": "Cut", "price": 1}),
        (ServiceUpdateRequest, {}),
        (StaffServiceAssignRequest, {"service_id": "s"}),
    ):
        with pytest.raises(ValidationError):
            model(duration_minutes=1441, **kw)


def test_booking_and_holiday_text_lengths():
    BookingCreateRequest(**_booking(customer_name="n" * 200, notes="x" * 1000, customer_phone="1" * 32))
    for over in ({"customer_name": "n" * 201}, {"notes": "x" * 1001}, {"customer_phone": "1" * 33}):
        with pytest.raises(ValidationError):
            BookingCreateRequest(**_booking(**over))
    HolidayCreateRequest(holiday_date="2030-01-01", title="t" * 200)
    with pytest.raises(ValidationError):
        HolidayCreateRequest(holiday_date="2030-01-01", title="t" * 201)


def test_action_request_total_price_stays_a_json_number():
    now = datetime.now(UTC)
    model = BookingActionRequestResponse(
        id="1", booking_id="2", kind="cancellation", status="pending", customer_name="A",
        start_datetime=now, total_price=Decimal("12.50"), created_at=now,
    )
    assert isinstance(model.total_price, Decimal)
    assert '"total_price":12.5' in model.model_dump_json()
    assert model.model_dump(mode="json")["total_price"] == 12.5


# -- d. list paging ------------------------------------------------------------


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1"])
def test_notifications_paging_bounds(query):
    assert _client(notifications.router).get(f"/v1/notifications?{query}").status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1"])
def test_booking_action_requests_paging_bounds(query):
    client = _client(booking_actions.router)
    assert client.get(f"/v1/booking-action-requests?{query}").status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1"])
def test_bookings_paging_bounds(query):
    assert _client(bookings.router).get(f"/v1/bookings?{query}").status_code == 422


def test_notifications_route_forwards_paging_by_keyword():
    use_cases = SimpleNamespace(list_notifications=AsyncMock(return_value=[]))
    with patch.object(notifications, "_use_cases", lambda session: use_cases):
        client = _client(notifications.router)
        assert client.get("/v1/notifications").status_code == 200
        assert client.get("/v1/notifications?limit=5&offset=10").status_code == 200
    calls = use_cases.list_notifications.await_args_list
    assert calls[0].kwargs == {"limit": None, "offset": 0}
    assert calls[1].kwargs == {"limit": 5, "offset": 10}


@pytest.mark.asyncio
async def test_notification_use_case_forwards_only_paging_the_caller_set():
    repo = SimpleNamespace(list_notifications=AsyncMock(return_value=[]))
    use_cases = NotificationUseCases(repo)
    actor = make_owner()
    await use_cases.list_notifications(actor)
    repo.list_notifications.assert_awaited_with(actor.id)
    await use_cases.list_notifications(actor, limit=5, offset=10)
    repo.list_notifications.assert_awaited_with(actor.id, limit=5, offset=10)
    await use_cases.list_notifications(actor, offset=3)
    repo.list_notifications.assert_awaited_with(actor.id, offset=3)


# -- e. batch notification delete ------------------------------------------------


def _delete_notifications(client, body):
    return client.request("DELETE", "/v1/notifications", json=body)


@pytest.mark.parametrize("body", [
    {}, {"ids": []}, {"ids": ["nope"]}, {"ids": [LOWER] * 101}, {"ids": [LOWER], "extra": 1}, {"ids": LOWER},
])
def test_notification_batch_delete_rejects_a_bad_body(body):
    assert _delete_notifications(_client(notifications.router), body).status_code == 422


def test_notification_batch_delete_without_a_body_is_422():
    assert _client(notifications.router).delete("/v1/notifications").status_code == 422


def test_notification_batch_delete_answers_204_and_hands_over_lowercase_ids():
    use_cases = SimpleNamespace(delete_many=AsyncMock(return_value=None))
    with patch.object(notifications, "_use_cases", lambda session: use_cases):
        response = _delete_notifications(_client(notifications.router), {"ids": [UPPER, LOWER]})
    assert response.status_code == 204 and response.content == b""
    assert use_cases.delete_many.await_args.args[1] == [LOWER, LOWER]


def test_notification_batch_delete_accepts_exactly_one_hundred_ids():
    use_cases = SimpleNamespace(delete_many=AsyncMock(return_value=None))
    with patch.object(notifications, "_use_cases", lambda session: use_cases):
        response = _delete_notifications(_client(notifications.router), {"ids": [LOWER] * 100})
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_notification_use_case_deletes_each_id_once_for_the_actor():
    repo = SimpleNamespace(delete_notifications=AsyncMock(return_value=None))
    actor = make_owner()
    await NotificationUseCases(repo).delete_many(actor, [LOWER, "b", LOWER])
    repo.delete_notifications.assert_awaited_once_with(actor.id, [LOWER, "b"])
