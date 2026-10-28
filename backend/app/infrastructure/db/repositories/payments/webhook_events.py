"""Webhook event intake."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.json_utils import decode_json


class WebhookEventMixin:
    """Webhook event storage and claiming."""

    session: AsyncSession

    # --------------------------------------------------------------- webhooks
    async def insert_webhook_event(
        self,
        *,
        provider: str,
        event_id: str,
        event_type: str,
        payload_hash: str,
        normalized: dict[str, Any],
        status: str = "received",
    ) -> str | None:
        """Replay gate: returns the new id, or None when this event was already stored."""

        result = await self.session.execute(
            text(
                """
                insert into payment_webhook_events
                  (provider_name, provider_event_reference, event_type, payload_hash,
                   normalized, processing_status, processed_at)
                values (:p, :e, :t, :h, cast(:n as jsonb), :s,
                        case when :s = 'received' then null else now() end)
                on conflict (provider_name, provider_event_reference) do nothing
                returning id
                """
            ),
            {
                "p": provider,
                "e": event_id,
                "t": event_type,
                "h": payload_hash,
                "n": json.dumps(normalized),
                "s": status,
            },
        )
        row = result.first()
        return str(row[0]) if row else None

    async def claim_webhook_event(
        self, event_id: str, stale_seconds: int, max_attempts: int
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                update payment_webhook_events
                set processing_status = 'processing', locked_at = now(),
                    attempts = attempts + 1
                where id = :id and attempts < :max
                  and ((processing_status in ('received', 'failed') and next_attempt_at <= now())
                    or (processing_status = 'processing'
                        and locked_at < now() - make_interval(secs => :stale)))
                returning id, provider_name, event_type, normalized, attempts
                """
            ),
            {"id": event_id, "max": max_attempts, "stale": float(stale_seconds)},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        data = dict(row)
        data["normalized"] = decode_json(data["normalized"])
        return data

    async def list_due_webhook_event_ids(
        self, stale_seconds: int, max_attempts: int, limit: int
    ) -> list[str]:
        result = await self.session.execute(
            text(
                """
                select id from payment_webhook_events
                where attempts < :max
                  and ((processing_status in ('received', 'failed') and next_attempt_at <= now())
                    or (processing_status = 'processing'
                        and locked_at < now() - make_interval(secs => :stale)))
                order by next_attempt_at
                limit :limit
                """
            ),
            {"max": max_attempts, "stale": float(stale_seconds), "limit": limit},
        )
        return [str(r[0]) for r in result.all()]

    async def finish_webhook_event(
        self, event_id: str, status: str, error_code: str | None = None, *, retry: bool = False
    ) -> None:
        """Mark an event done, or schedule exponential backoff when ``retry``."""

        await self.session.execute(
            text(
                """
                update payment_webhook_events
                set processing_status = :s, last_error_code = :e, locked_at = null,
                    processed_at = case when :s in ('processed', 'ignored') then now()
                                        else processed_at end,
                    next_attempt_at = case when :retry
                      then now() + make_interval(secs => least(power(2, attempts) * 10, 3600))
                      else next_attempt_at end
                where id = :id
                """
            ),
            {"id": event_id, "s": status, "e": error_code, "retry": retry},
        )
