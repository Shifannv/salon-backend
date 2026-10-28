"""Notification and device use cases."""

from typing import Any

from app.application.use_cases.paging import paging_kwargs
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository


class NotificationUseCases:
    """Notification and device use cases."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    async def list_notifications(
        self, actor: Profile, *, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List actor notifications, newest first.

        Without ``limit`` the repository applies its safety ceiling; ``limit`` and
        ``offset`` are forwarded only when the caller set them.
        """

        return await self.repository.list_notifications(actor.id, **paging_kwargs(limit, offset))

    async def mark_read(self, actor: Profile, notification_id: str) -> dict[str, Any]:
        """Mark notification as read."""

        return await self.repository.mark_notification_read(actor.id, notification_id)

    async def mark_all_read(self, actor: Profile) -> int:
        """Mark all unread notifications owned by the actor."""

        return await self.repository.mark_all_notifications_read(actor.id)

    async def register_device(
        self,
        actor: Profile,
        token: str,
        platform: str | None,
        device_name: str | None,
    ) -> dict[str, Any]:
        """Register actor device token (idempotent — reactivates if it already exists)."""

        return await self.repository.register_device(actor.id, token, platform, device_name)

    async def deactivate_device(self, actor: Profile, token: str) -> None:
        """Deactivate this specific device token for the actor."""

        await self.repository.deactivate_device_for_actor(actor.id, token)
