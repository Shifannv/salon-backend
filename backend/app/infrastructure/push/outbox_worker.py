"""Retryable notification-outbox delivery using independent DB sessions."""

import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.push.fcm_gateway import FCMGateway

_log = logging.getLogger(__name__)
_POLL_SECONDS = 15  # pause between outbox polls


async def deliver_notification_outbox_event(outbox_id: str) -> None:
    """Claim and deliver one persisted event after its transaction commits."""

    async with AsyncSessionLocal() as session:
        repository = PlatformRepository(session)
        event = await repository.get_notification_outbox_event(outbox_id)
        if event is None:
            return
        try:
            gateway = FCMGateway(settings, session)
            await gateway.fan_out(event["notification_id"], event["user_id"])
            if await repository.notification_has_failed_delivery(
                event["notification_id"]
            ):
                await repository.mark_notification_outbox_retry(
                    outbox_id, "Push provider did not accept one or more deliveries"
                )
            else:
                await repository.mark_notification_outbox_processed(outbox_id)
        except Exception as exc:
            _log.warning("Push outbox delivery failed for %s", outbox_id)
            await repository.mark_notification_outbox_retry(
                outbox_id, type(exc).__name__
            )


async def enqueue_and_deliver_notification(
    *,
    user_id: str,
    booking_id: str | None,
    notification_type: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Persist a notification (booking-linked or not), then attempt push delivery."""

    async with AsyncSessionLocal() as session:
        repository = PlatformRepository(session)
        outbox_id = await repository.enqueue_notification(
            user_id=user_id,
            booking_id=booking_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )
    await deliver_notification_outbox_event(outbox_id)


async def drain_notification_outbox(limit: int = 50) -> int:
    """Attempt each due event once; concurrent workers claim by update."""

    async with AsyncSessionLocal() as session:
        ids = await PlatformRepository(session).list_due_notification_outbox_ids(limit)
    for outbox_id in ids:
        await deliver_notification_outbox_event(outbox_id)
    return len(ids)


async def run_forever() -> None:
    """Poll the durable queue for missed and failed push deliveries."""

    while True:
        try:
            await drain_notification_outbox()
        except Exception:
            _log.exception("Notification outbox poll failed")
        await asyncio.sleep(_POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_forever())
