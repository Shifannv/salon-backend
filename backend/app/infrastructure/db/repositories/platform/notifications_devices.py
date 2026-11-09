"""In-app notifications and push devices."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
)
from app.infrastructure.db.repositories.platform._sql import page_bounds


class NotificationsDevicesMixin:
    """In-app notifications and push devices."""

    session: AsyncSession

    async def list_notifications(
        self, actor_id: str, *, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List actor notifications, newest first, bounded by the list safety ceiling."""

        result = await self.session.execute(
            text(
                """
                select id, user_id, booking_id, type, title, body, read, read_at, created_at
                from notifications
                where user_id = :actor_id and deleted_at is null
                order by created_at desc, id desc
                limit :limit offset :offset
                """
            ),
            {"actor_id": actor_id, **page_bounds(limit, offset)},
        )
        rows = []
        for row in result.mappings().all():
            r = dict(row)
            for col in ("id", "user_id", "booking_id"):
                if r.get(col) is not None:
                    r[col] = str(r[col])
            rows.append(r)
        return rows

    async def mark_notification_read(self, actor_id: str, notification_id: str) -> dict[str, Any]:
        """Mark one notification as read."""

        result = await self.session.execute(
            text(
                """
                update notifications
                set read = true
                where id = :notification_id and user_id = :actor_id and deleted_at is null
                returning id, user_id, booking_id, type, title, body, read, read_at, created_at
                """
            ),
            {"actor_id": actor_id, "notification_id": notification_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Notification not found")
        await self.session.commit()
        r = dict(row)
        for col in ("id", "user_id", "booking_id"):
            if r.get(col) is not None:
                r[col] = str(r[col])
        return r

    async def mark_all_notifications_read(self, actor_id: str) -> int:
        """Mark every unread notification owned by an actor."""

        result = await self.session.execute(
            text(
                """
                with updated as (
                  update notifications
                  set read = true
                  where user_id = :actor_id and not read and deleted_at is null
                  returning 1
                )
                select count(*) from updated
                """
            ),
            {"actor_id": actor_id},
        )
        updated_count = int(result.scalar_one())
        await self.session.commit()
        return updated_count

    async def delete_notifications(self, actor_id: str, ids: list[str]) -> None:
        """Dismiss the actor's own notifications; ids that are unknown, foreign or gone are ignored."""

        await self.session.execute(
            text(
                """
                update notifications
                set deleted_at = now()
                where id = any(cast(:ids as uuid[])) and user_id = :actor_id and deleted_at is null
                """
            ),
            {"actor_id": actor_id, "ids": ids},
        )
        await self.session.commit()

    async def purge_notifications(
        self, *, dismissed_days: int, max_age_days: int, limit: int
    ) -> int:
        """Delete up to ``limit`` dismissed or expired notifications; returns the rows removed.

        Outbox and delivery rows go with them through their ON DELETE CASCADE keys.
        """

        # Two statements, each served by its own index (an OR would force a full bitmap scan).
        # The conditions are fixed constants; never build one from caller input.
        conditions = (
            ("deleted_at < now() - make_interval(days => :days)", dismissed_days),
            ("created_at < now() - make_interval(days => :days)", max_age_days),
        )
        removed = 0
        for condition, days in conditions:
            if removed >= limit:
                break
            result = await self.session.execute(
                text(
                    f"""
                    with doomed as (
                      select id from notifications where {condition} limit :limit
                    ), removed as (
                      delete from notifications n using doomed d where n.id = d.id returning 1
                    )
                    select count(*) from removed
                    """
                ),
                {"days": days, "limit": limit - removed},
            )
            removed += int(result.scalar_one())
        await self.session.commit()
        return removed

    # register_device with actor_id is defined in the section below (line ~1334)

    async def deactivate_device(self, token: str) -> None:
        """Deactivate this actor's device token through the database function."""

        await self.session.execute(
            text("select deactivate_device_token(:token)"),
            {"token": token},
        )
        await self.session.commit()

    async def deactivate_device_for_actor(self, actor_id: str, token: str) -> None:
        """Deactivate a device token only if it belongs to the given actor.

        Preferred over deactivate_device() when we have a verified actor_id,
        because the DB function relies on auth.uid() which is unavailable via
        the privileged Postgres role.
        """

        await self.session.execute(
            text(
                "update device_tokens set is_active = false where token = :token and user_id = :actor_id"
            ),
            {"token": token, "actor_id": actor_id},
        )
        await self.session.commit()

    # ------------------------------------------------------------------
    # Admin — salon management
    # ------------------------------------------------------------------

    async def register_device(
        self,
        actor_id: str,
        token: str,
        platform: str | None,
        device_name: str | None,
    ) -> dict[str, Any]:
        """Register (or reactivate) a device token, linked to actor_id."""

        # We use a direct upsert rather than the DB function so we can pass
        # the actor_id without relying on auth.uid() (which doesn't work via
        # the privileged Postgres role).
        result = await self.session.execute(
            text(
                """
                insert into device_tokens (user_id, token, platform, device_name, is_active, last_seen_at)
                values (:user_id, :token, :platform, :device_name, true, now())
                on conflict (token) do update
                  set user_id      = :user_id,
                      is_active    = true,
                      platform     = coalesce(:platform, device_tokens.platform),
                      device_name  = coalesce(:device_name, device_tokens.device_name),
                      last_seen_at = now()
                returning id, token, platform
                """
            ),
            {
                "user_id": actor_id,
                "token": token,
                "platform": platform,
                "device_name": device_name,
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def create_notification(
        self,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str | None,
    ) -> dict[str, Any]:
        """Create a notification record and return it."""

        result = await self.session.execute(
            text(
                """
                insert into notifications (user_id, booking_id, type, title, body)
                values (:user_id, :booking_id, :type, :title, :body)
                returning id, user_id, booking_id, type, title, body, read, read_at, created_at
                """
            ),
            {
                "user_id": user_id,
                "booking_id": booking_id,
                "type": notification_type,
                "title": title,
                "body": body,
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())
