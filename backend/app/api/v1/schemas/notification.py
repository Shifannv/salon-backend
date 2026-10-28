"""Notification and device API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.api.v1.schemas.common import IdStr


class NotificationResponse(BaseModel):
    """Notification response."""

    id: IdStr
    user_id: IdStr
    booking_id: IdStr | None = None
    type: str | None = None
    title: str
    body: str | None = None
    read: bool
    read_at: datetime | None = None  # set when read flips true (migration 0002)
    created_at: datetime



class MarkAllNotificationsReadResponse(BaseModel):
    """Number of unread notifications marked as read."""

    updated_count: int = Field(ge=0)


class DeviceRegisterRequest(BaseModel):
    """Device registration request."""

    token: str
    platform: str | None = None
    device_name: str | None = None


class DeviceRegisterResponse(BaseModel):
    """Device registration response."""

    id: IdStr
    token: str
    platform: str | None = None
