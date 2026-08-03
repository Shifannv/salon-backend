from datetime import datetime

from app.schemas.common import APIModel


class NotificationOut(APIModel):
    id: str
    user_id: str
    booking_id: str | None
    type: str | None
    title: str
    body: str | None
    read: bool
    created_at: datetime


class DeviceTokenIn(APIModel):
    token: str
    platform: str | None = None
    device_name: str | None = None


class DeviceTokenOut(APIModel):
    id: str
    token: str
    platform: str | None
    device_name: str | None
    is_active: bool

