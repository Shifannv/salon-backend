"""Email outbox drainer. Claims commit before provider calls, with replay-safe retries."""

import asyncio
import logging

from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.email.resend import ResendEmailGateway

_log = logging.getLogger(__name__)


async def deliver_once(session_factory=AsyncSessionLocal, gateway=None):
    gateway = gateway or ResendEmailGateway(settings)
    if not gateway.enabled:
        return False
    async with session_factory() as session:
        # Resend's idempotency window is 24h. Stop ambiguous retries before it elapses.
        await session.execute(text("""
            update email_events set status='failed',last_error_code='delivery_window_expired'
            where status in ('pending','processing') and created_at < now() - interval '23 hours'
        """))
        await session.execute(text("""
            update email_events set status='failed',last_error_code='delivery_attempts_exhausted'
            where attempts >= :max and (status='pending'
              or (status='processing' and locked_at < now() - interval '5 minutes'))
        """), {"max":settings.email_max_attempts})
        event = (await session.execute(text("""
            with claim as (
              select id from email_events where attempts < :max
                and ((status='pending' and next_attempt_at <= now())
                  or (status='processing' and locked_at < now() - interval '5 minutes'))
              order by next_attempt_at for update skip locked limit 1
            ) update email_events e set status='processing',locked_at=now(),attempts=attempts+1
              from claim where e.id=claim.id returning e.*
        """), {"max": settings.email_max_attempts})).mappings().one_or_none()
        await session.commit()
    if event is None:
        return False
    try:
        provider_id = await gateway.send(recipient=event["recipient"], subject=event["subject"],
                                         body=event["body"], event_key=event["event_key"])
    except Exception:
        _log.error("ALERT email_delivery failed event_id=%s", event["id"])
        async with session_factory() as session:
            await session.execute(text("""
                update email_events set status=case when attempts >= :max then 'failed' else 'pending' end,
                  last_error_code='provider_unavailable',locked_at=null,
                  next_attempt_at=now() + make_interval(secs => :delay) where id=:id
            """), {"id":event["id"],"max":settings.email_max_attempts,"delay":min(3600, 30 * 2 ** event["attempts"])})
            await session.commit()
    else:
        async with session_factory() as session:
            await session.execute(text("update email_events set status='sent',provider_message_id=:ref,sent_at=now(),locked_at=null,last_error_code=null where id=:id"), {"id":event["id"],"ref":provider_id})
            await session.commit()
    return True


async def main():
    configure_logging()
    while True:
        try:
            worked = await deliver_once()
        except Exception:
            _log.error("ALERT email_delivery worker_unavailable")
            worked = False
        await asyncio.sleep(0.1 if worked else settings.email_worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(main())
