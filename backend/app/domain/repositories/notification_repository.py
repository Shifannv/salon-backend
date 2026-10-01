"""Notification and device repository port."""

from typing import Any, Protocol


class NotificationRepository(Protocol):
    """Persistence port for notifications and device tokens."""

    async def list_notifications(self, actor_id: str) -> list[dict[str, Any]]:
        """Return notifications addressed to actor_id ordered newest-first."""

    async def mark_notification_read(
        self, actor_id: str, notification_id: str
    ) -> dict[str, Any]:
        """Mark a notification read. Raises NotFoundError if not owned by actor."""

    async def mark_all_notifications_read(self, actor_id: str) -> int:
        """Mark every unread notification owned by the actor and return the count."""

    async def create_notification(
        self,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str | None,
    ) -> dict[str, Any]:
        """Insert a notifications row and return it."""

    async def register_device(
        self,
        actor_id: str,
        token: str,
        platform: str | None,
        device_name: str | None,
    ) -> dict[str, Any]:
        """Upsert a device_tokens row (idempotent — reactivates if exists)."""

    async def deactivate_device_for_actor(self, actor_id: str, token: str) -> None:
        """Deactivate a device token only if it belongs to actor_id."""
