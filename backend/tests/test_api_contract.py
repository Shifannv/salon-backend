"""HTTP contract smoke tests shared by the customer and owner apps."""

from fastapi.testclient import TestClient

from app.main import app


def test_openapi_contains_new_cross_app_endpoints() -> None:
    paths = app.openapi()["paths"]

    assert "/v1/bookings/{booking_id}/delay" in paths
    assert "/v1/notifications/read-all" in paths
    assert paths["/v1/salons/me/holidays/{holiday_id}"]["delete"]["responses"].get("204")
    batch_delete = paths["/v1/notifications"]["delete"]
    assert batch_delete["responses"].get("204")
    assert batch_delete["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DeleteNotificationsRequest"
    )
    assert "/v1/booking-action-requests" in paths
    assert "/v1/booking-action-requests/{request_id}/respond" in paths
    assert "/v1/bookings/{booking_id}/payment-confirmation-requests" in paths
    assert "/v1/bookings/{booking_id}/cancellation-requests" in paths
    assert "/v1/salons/me/closures/preview" in paths
    assert "/v1/salons/me/closures" in paths
    assert "/v1/salons/me/payout-account" in paths
    assert "/v1/salons/me/setup-status" in paths
    assert "/v1/salons/me/payout-account/history" in paths
    assert "/v1/payments/config" in paths
    assert "/v1/bookings/{booking_id}/payments/intent" in paths
    assert "/v1/salons/me/earnings" in paths
    # The pre-existing manual receipt route keeps its contract.
    assert "/v1/bookings/{booking_id}/payment" in paths
    assert "/v1/webhooks/{provider}" not in paths  # dormant until a provider is configured


def test_request_validation_uses_shared_error_envelope() -> None:
    response = TestClient(app).get("/v1/availability")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed"
    assert isinstance(payload["error"]["details"], list)
