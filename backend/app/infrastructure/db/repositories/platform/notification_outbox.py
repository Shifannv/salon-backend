"""Notification outbox writes and worker reads."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class NotificationOutboxMixin:
    """Notification outbox writes and worker reads."""

    session: AsyncSession

    async def _insert_notification_outbox(
        self,
        *,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Persist a notification and retryable push event in this transaction."""

        result = await self.session.execute(
            text(
                """
                with created_notification as (
                  insert into notifications (user_id, booking_id, type, title, body, data)
                  values (:user_id, :booking_id, :notification_type, :title, :body,
                          cast(:data as jsonb))
                  returning id, user_id
                )
                insert into notification_outbox (notification_id, user_id)
                select id, user_id from created_notification
                returning id
                """
            ),
            {
                "user_id": user_id,
                "booking_id": booking_id,
                "notification_type": notification_type,
                "title": title,
                "body": body,
                "data": json.dumps(data) if data else None,
            },
        )
        return str(result.scalar_one())

    async def enqueue_notification(
        self,
        *,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Persist a notification/outbox pair outside another state transaction."""

        outbox_id = await self._insert_notification_outbox(
            user_id=user_id,
            booking_id=booking_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )
        await self.session.commit()
        return outbox_id

    async def get_notification_outbox_event(
        self, outbox_id: str
    ) -> dict[str, Any] | None:
        """Claim a due outbox event for one background delivery attempt."""

        result = await self.session.execute(
            text(
                """
                update notification_outbox
                set attempts = attempts + 1,
                    next_attempt_at = now() + interval '5 minutes'
                where id = :outbox_id
                  and status = 'pending'
                  and next_attempt_at <= now()
                returning id, notification_id, user_id
                """
            ),
            {"outbox_id": outbox_id},
        )
        row = result.mappings().one_or_none()
        await self.session.commit()
        if row is None:
            return None
        return {key: str(value) for key, value in dict(row).items()}

    async def list_due_notification_outbox_ids(self, limit: int = 50) -> list[str]:
        """Find persisted push events due for an attempt or retry."""

        result = await self.session.execute(
            text(
                """
                select id from notification_outbox
                where status = 'pending' and next_attempt_at <= now()
                order by next_attempt_at, created_at
                limit :limit
                """
            ),
            {"limit": limit},
        )
        return [str(row[0]) for row in result.all()]

    async def notification_has_failed_delivery(self, notification_id: str) -> bool:
        """Detect provider failures for still-active device tokens."""

        result = await self.session.execute(
            text(
                """
                select exists (
                  select 1 from notification_deliveries delivery
                  join device_tokens device on device.id = delivery.device_token_id
                  where delivery.notification_id = :notification_id
                    and not delivery.delivered
                    and device.is_active
                )
                """
            ),
            {"notification_id": notification_id},
        )
        return bool(result.scalar_one())

    async def mark_notification_outbox_processed(self, outbox_id: str) -> None:
        """Mark an outbox event processed after push fan-out returns."""

        await self.session.execute(
            text(
                """
                update notification_outbox
                set status = 'processed', processed_at = now(), last_error = null
                where id = :outbox_id
                """
            ),
            {"outbox_id": outbox_id},
        )
        await self.session.commit()

    async def mark_notification_outbox_retry(
        self, outbox_id: str, error: str
    ) -> None:
        """Persist a safe failure message and leave the event retryable."""

        await self.session.execute(
            text(
                """
                update notification_outbox
                set last_error = :error,
                    next_attempt_at = now() + interval '5 minutes'
                where id = :outbox_id and status = 'pending'
                """
            ),
            {"outbox_id": outbox_id, "error": error[:1000]},
        )
        await self.session.commit()
