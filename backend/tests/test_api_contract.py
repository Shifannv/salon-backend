"""HTTP contract smoke tests shared by the customer and owner apps."""

from fastapi.testclient import TestClient

from app.main import app


def test_openapi_contains_new_cross_app_endpoints() -> None:
    paths = app.openapi()["paths"]

    assert "/v1/bookings/{booking_id}/delay" in paths
    assert "/v1/notifications/read-all" in paths
    assert paths["/v1/salons/me/holidays/{holiday_id}"]["delete"]["responses"].get("204")


def test_request_validation_uses_shared_error_envelope() -> None:
    response = TestClient(app).get("/v1/availability")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed"
    assert isinstance(payload["error"]["details"], list)
