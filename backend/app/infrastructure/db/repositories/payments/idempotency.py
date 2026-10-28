"""Idempotency-key persistence."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IdempotencyInProgressError, IdempotencyKeyReuseError
from app.infrastructure.db.json_utils import decode_json


class IdempotencyMixin:
    """Reservation and replay of idempotent requests."""

    session: AsyncSession

    async def release_idempotent(self, actor_id: str, scope: str, key: str) -> None:
        """Drop an UNFINISHED reservation so the client may retry with the same key."""

        await self.session.execute(
            text(
                """
                delete from payment_idempotency_keys
                where actor_id = :a and scope = :s and idempotency_key = :k
                  and response_body is null
                """
            ),
            {"a": actor_id, "s": scope, "k": key},
        )

    # ------------------------------------------------------------ idempotency
    async def begin_idempotent(
        self, actor_id: str, scope: str, key: str, fingerprint: str, ttl_seconds: int
    ) -> dict[str, Any] | None:
        """Reserve ``key`` or return the stored response of its first, completed use.

        The reservation lives in the caller's transaction, so a concurrent duplicate
        blocks on the unique index until the first request commits, then replays it. A
        key reused with a different request body raises ``IdempotencyKeyReuseError``.
        """

        params = {"a": actor_id, "s": scope, "k": key}
        await self.session.execute(
            text(
                """
                delete from payment_idempotency_keys
                where actor_id = :a and scope = :s and idempotency_key = :k
                  and expires_at < now()
                """
            ),
            params,
        )
        inserted = await self.session.execute(
            text(
                """
                insert into payment_idempotency_keys
                  (actor_id, scope, idempotency_key, request_fingerprint, expires_at)
                values (:a, :s, :k, :f, now() + make_interval(secs => :ttl))
                on conflict (actor_id, scope, idempotency_key) do nothing
                returning id
                """
            ),
            {**params, "f": fingerprint, "ttl": float(ttl_seconds)},
        )
        if inserted.first() is not None:
            return None
        existing = (
            await self.session.execute(
                text(
                    """
                    select request_fingerprint, response_body
                    from payment_idempotency_keys
                    where actor_id = :a and scope = :s and idempotency_key = :k
                    """
                ),
                params,
            )
        ).mappings().one()
        if existing["request_fingerprint"] != fingerprint:
            raise IdempotencyKeyReuseError(
                "Idempotency-Key was already used for a different request"
            )
        body = decode_json(existing["response_body"])
        if body is None:
            raise IdempotencyInProgressError("The original request is still being processed")
        return body

    async def finish_idempotent(
        self, actor_id: str, scope: str, key: str, status_code: int, body: dict[str, Any]
    ) -> None:
        await self.session.execute(
            text(
                """
                update payment_idempotency_keys
                set response_status = :st, response_body = cast(:b as jsonb)
                where actor_id = :a and scope = :s and idempotency_key = :k
                """
            ),
            {"a": actor_id, "s": scope, "k": key, "st": status_code, "b": json.dumps(body, default=str)},
        )

    async def purge_expired_idempotency(self) -> int:
        result = await self.session.execute(
            text("delete from payment_idempotency_keys where expires_at < now()")
        )
        return result.rowcount or 0
