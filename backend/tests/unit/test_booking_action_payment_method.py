"""payment_method belongs to the owner's respond call, not the customer's claim call."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.routes import booking_actions
from app.core.exceptions import register_exception_handlers
from tests.conftest import make_owner

ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ROW = {
    "id": ID, "booking_id": ID, "kind": "payment_confirmation", "status": "pending",
    "customer_name": "A", "start_datetime": datetime(2030, 1, 1, 10, tzinfo=UTC),
    "total_price": 100, "created_at": datetime(2030, 1, 1, 9, tzinfo=UTC),
}


def _call(path, json, use_cases):
    app = FastAPI()
    app.include_router(booking_actions.router, prefix="/v1")
    register_exception_handlers(app)
    app.dependency_overrides[get_current_actor] = lambda: make_owner()
    app.dependency_overrides[get_authenticated_session] = lambda: Mock()
    with patch.object(booking_actions, "_action_use_cases", lambda session: use_cases):
        return TestClient(app, raise_server_exceptions=False).post(path, json=json)


def test_customer_payment_claim_does_not_send_a_payment_method():
    use_cases = SimpleNamespace(create_customer_request=AsyncMock(return_value=ROW))
    response = _call(f"/v1/bookings/{ID}/payment-confirmation-requests", {}, use_cases)
    assert response.status_code == 201
    assert "payment_method" not in use_cases.create_customer_request.await_args.kwargs


def test_owner_receipt_forwards_the_payment_method():
    use_cases = SimpleNamespace(respond=AsyncMock(return_value=ROW))
    response = _call(
        f"/v1/booking-action-requests/{ID}/respond",
        {"decision": "received", "payment_method": "online"}, use_cases,
    )
    assert response.status_code == 200
    assert use_cases.respond.await_args.kwargs["payment_method"] == "online"


def test_owner_receipt_defaults_to_cash():
    use_cases = SimpleNamespace(respond=AsyncMock(return_value=ROW))
    _call(f"/v1/booking-action-requests/{ID}/respond", {"decision": "received"}, use_cases)
    assert use_cases.respond.await_args.kwargs["payment_method"] == "cash"
