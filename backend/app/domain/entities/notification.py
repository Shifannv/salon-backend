"""Notification and device domain entities."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Notification:
    """An in-app push notification addressed to a single user."""

    id: str
    user_id: str
    booking_id: str | None
    type: str | None
    title: str
    body: str | None
    read: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DeviceToken:
    """A single physical device registered for push delivery."""

    id: str
    user_id: str
    token: str
    platform: str | None
    device_name: str | None
    is_active: bool
    last_seen_at: datetime
    created_at: datetime
