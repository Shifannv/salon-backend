"""Unit tests for notification API schemas."""

from datetime import UTC, datetime
from uuid import uuid4

from app.api.v1.schemas.platform import DeviceRegisterResponse, NotificationResponse


def test_notification_response_converts_database_uuids_to_strings() -> None:
    notification_id = uuid4()
    user_id = uuid4()
    booking_id = uuid4()

    response = NotificationResponse(
        id=notification_id,
        user_id=user_id,
        booking_id=booking_id,
        title="Booking Confirmed",
        read=False,
        created_at=datetime.now(UTC),
    )

    assert response.id == str(notification_id)
    assert response.user_id == str(user_id)
    assert response.booking_id == str(booking_id)


def test_notification_response_allows_missing_booking_id() -> None:
    response = NotificationResponse(
        id=uuid4(),
        user_id=uuid4(),
        booking_id=None,
        title="General notification",
        read=False,
        created_at=datetime.now(UTC),
    )

    assert response.booking_id is None


def test_device_register_response_converts_database_uuid_to_string() -> None:
    device_id = uuid4()

    response = DeviceRegisterResponse(
        id=device_id,
        token="device-token",
        platform="android",
    )

    assert response.id == str(device_id)
