"""Notification and device API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    audience: str | None = None



class DeleteNotificationsRequest(BaseModel):
    """Notifications the caller dismissed; ids that are not theirs are ignored."""

    model_config = ConfigDict(extra="forbid")

    ids: list[UUID] = Field(min_length=1, max_length=100)


class MarkAllNotificationsReadResponse(BaseModel):
    """Number of unread notifications marked as read."""

    updated_count: int = Field(ge=0)


class DeviceRegisterRequest(BaseModel):
    """Device registration request."""

    token: str
    platform: str | None = None
    device_name: str | None = None
    app: str | None = None


class DeviceRegisterResponse(BaseModel):
    """Device registration response."""

    id: IdStr
    token: str
    platform: str | None = None
