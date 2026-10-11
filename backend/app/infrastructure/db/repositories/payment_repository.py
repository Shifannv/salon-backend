"""Raw-SQL repository for the payment ledger, refunds, webhook intake and idempotency.

Kept apart from ``platform_repository.py`` on purpose. Amounts are only ever read here
(``bookings.total_price`` / ``deposit_amount`` were computed in SQL); nothing recomputes
a price. Booking-level payment columns are written solely by the database's
``recompute_booking_payment_state`` trigger path.
"""

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IdempotencyInProgressError, IdempotencyKeyReuseError

_SETTLED = "('captured', 'partially_refunded', 'refunded')"
_OPEN = "('created', 'authorized')"


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


class PaymentRepository:
    """Database adapter for payments."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

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
        body = _json(existing["response_body"])
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
            {"a": actor_id, "s": scope, "k": key, "st": status_code, "b": json.dumps(body)},
        )

    async def purge_expired_idempotency(self) -> int:
        result = await self.session.execute(
            text("delete from payment_idempotency_keys where expires_at < now()")
        )
        return result.rowcount or 0

    # --------------------------------------------------------------- bookings
    async def lock_booking(self, booking_id: str, actor_id: str) -> dict[str, Any] | None:
        """Lock a booking and report the actor's relationship to it."""

        result = await self.session.execute(
            text(
                """
                select b.id, b.salon_id, b.customer_id, b.status, b.total_price,
                       b.deposit_amount, b.paid_amount, b.refunded_amount, b.currency,
                       b.payment_status, b.payment_preference, s.owner_id,
                       exists (select 1 from staff st
                               where st.salon_id = b.salon_id and st.profile_id = :actor
                                 and st.is_active) as actor_is_staff
                from bookings b join salons s on s.id = b.salon_id
                where b.id = :booking_id
                for update of b
                """
            ),
            {"booking_id": booking_id, "actor": actor_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def read_booking(self, booking_id: str, actor_id: str) -> dict[str, Any] | None:
        """Same shape as ``lock_booking`` without locking (read endpoints)."""

        result = await self.session.execute(
            text(
                """
                select b.id, b.salon_id, b.customer_id, b.status, b.total_price,
                       b.deposit_amount, b.paid_amount, b.refunded_amount, b.currency,
                       b.payment_status, b.payment_preference, s.owner_id,
                       exists (select 1 from staff st
                               where st.salon_id = b.salon_id and st.profile_id = :actor
                                 and st.is_active) as actor_is_staff
                from bookings b join salons s on s.id = b.salon_id
                where b.id = :booking_id
                """
            ),
            {"booking_id": booking_id, "actor": actor_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    # ----------------------------------------------------------------- ledger
    _PAYMENT_COLUMNS = """
        id, booking_id, salon_id, channel, purpose, settlement_model, provider, method,
        instrument, amount, currency, status, failure_code, expires_at, captured_at,
        created_at, order_ref, payment_ref, intent_reference, platform_fee_amount
    """

    async def expire_stale_open_intents(self, booking_id: str) -> None:
        await self.session.execute(
            text(
                f"""
                update booking_payments set status = 'expired'
                where booking_id = :b and channel = 'gateway' and status in {_OPEN}
                  and expires_at is not null and expires_at < now()
                """
            ),
            {"b": booking_id},
        )

    async def get_open_intent(self, booking_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                f"""
                select {self._PAYMENT_COLUMNS} from booking_payments
                where booking_id = :b and channel = 'gateway' and status in {_OPEN}
                limit 1
                """
            ),
            {"b": booking_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def insert_intent(
        self,
        *,
        booking: dict[str, Any],
        actor_id: str,
        purpose: str,
        amount: Decimal,
        platform_fee: Decimal,
        provider: str,
        settlement_model: str,
        intent_reference: str,
        expires_in_seconds: int,
    ) -> str:
        result = await self.session.execute(
            text(
                """
                insert into booking_payments
                  (booking_id, salon_id, payer_id, recorded_by, channel, purpose,
                   settlement_model, provider, amount, platform_fee_amount, currency,
                   status, intent_reference, expires_at)
                values (:booking_id, :salon_id, :actor, :actor, 'gateway', :purpose,
                        :settlement, :provider, :amount, :fee, :currency, 'created',
                        :ref, now() + make_interval(secs => :ttl))
                returning id
                """
            ),
            {
                "booking_id": booking["id"],
                "salon_id": booking["salon_id"],
                "actor": actor_id,
                "purpose": purpose,
                "settlement": settlement_model,
                "provider": provider,
                "amount": amount,
                "fee": platform_fee,
                "currency": booking["currency"],
                "ref": intent_reference,
                "ttl": float(expires_in_seconds),
            },
        )
        return str(result.scalar_one())

    async def set_intent_order(self, payment_id: str, order_ref: str) -> None:
        await self.session.execute(
            text("update booking_payments set order_ref = :o where id = :id"),
            {"o": order_ref, "id": payment_id},
        )

    async def cancel_open_intent(self, booking_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                f"""
                update booking_payments set status = 'cancelled'
                where booking_id = :b and channel = 'gateway' and status in {_OPEN}
                returning {self._PAYMENT_COLUMNS}
                """
            ),
            {"b": booking_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def get_payment_by_order(self, booking_id: str, order_ref: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                f"""
                select {self._PAYMENT_COLUMNS} from booking_payments
                where booking_id = :b and order_ref = :o and channel = 'gateway'
                """
            ),
            {"b": booking_id, "o": order_ref},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def get_payment(self, booking_id: str, payment_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                f"""
                select {self._PAYMENT_COLUMNS} from booking_payments
                where booking_id = :b and id = :id for update
                """
            ),
            {"b": booking_id, "id": payment_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def list_payments(self, booking_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                f"""
                select {self._PAYMENT_COLUMNS} from booking_payments
                where booking_id = :b order by created_at, id
                """
            ),
            {"b": booking_id},
        )
        return [dict(r) for r in result.mappings().all()]

    async def list_refunds(self, booking_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                select id, payment_id, amount, status, reason, created_at, processed_at
                from payment_refunds where booking_id = :b order by created_at, id
                """
            ),
            {"b": booking_id},
        )
        return [dict(r) for r in result.mappings().all()]

    # ---------------------------------------------------------------- refunds
    async def refunded_or_pending(self, payment_id: str) -> Decimal:
        result = await self.session.execute(
            text(
                """
                select coalesce(sum(amount), 0) from payment_refunds
                where payment_id = :p and status <> 'failed'
                """
            ),
            {"p": payment_id},
        )
        return Decimal(result.scalar_one())

    async def insert_refund(
        self,
        *,
        payment: dict[str, Any],
        actor_id: str,
        amount: Decimal,
        reason: str | None,
        idempotency_key: str,
    ) -> str:
        result = await self.session.execute(
            text(
                """
                insert into payment_refunds
                  (payment_id, booking_id, provider, amount, status, reason,
                   idempotency_key, requested_by)
                values (:p, :b, :provider, :amount, 'created', :reason, :k, :actor)
                returning id
                """
            ),
            {
                "p": payment["id"],
                "b": payment["booking_id"],
                "provider": payment["provider"],
                "amount": amount,
                "reason": reason,
                "k": idempotency_key,
                "actor": actor_id,
            },
        )
        return str(result.scalar_one())

    async def update_refund(
        self, refund_id: str, refund_ref: str, status: str, failure_code: str | None
    ) -> None:
        await self.session.execute(
            text(
                """
                update payment_refunds
                set refund_ref = :r, status = :s, failure_code = :f,
                    processed_at = case when :s = 'processed' then now() else processed_at end
                where id = :id
                """
            ),
            {"r": refund_ref, "s": status, "f": failure_code, "id": refund_id},
        )

    async def apply_refund_observation(
        self, provider: str, refund_ref: str, status: str, failure_code: str | None
    ) -> str:
        result = await self.session.execute(
            text(
                """
                update payment_refunds
                set status = :s, failure_code = :f,
                    processed_at = case when :s = 'processed' then now() else processed_at end
                where provider = :p and refund_ref = :r and status = 'created'
                returning id
                """
            ),
            {"p": provider, "r": refund_ref, "s": status, "f": failure_code},
        )
        return "applied" if result.first() is not None else "ignored"

    # ------------------------------------------------------ observed payments
    async def apply_payment_observation(
        self,
        *,
        provider: str,
        order_ref: str | None,
        payment_ref: str | None,
        status: str,
        amount: Decimal | None,
        currency: str | None,
        instrument: str | None,
        failure_code: str | None,
    ) -> str:
        """Fold a provider-reported payment state into the ledger.

        Shared by webhooks, the client callback and reconciliation. Returns one of
        ``applied``, ``ignored`` (stale or out of order), ``unmatched``, ``mismatch``
        (amount or currency differs; the row is failed and the booking is never marked
        paid) or ``overcollection`` (the database refused to over-collect).
        """

        from app.domain.entities.payment import is_forward_transition

        result = await self.session.execute(
            text(
                """
                select id, status, amount, currency from booking_payments
                where provider = :p and channel = 'gateway'
                  and ((cast(:o as text) is not null and order_ref = cast(:o as text))
                    or (cast(:pr as text) is not null and payment_ref = cast(:pr as text)))
                limit 1
                for update
                """
            ),
            {"p": provider, "o": order_ref, "pr": payment_ref},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return "unmatched"
        if not is_forward_transition(row["status"], status):
            return "ignored"
        outcome = "applied"
        failure = failure_code
        if status in {"authorized", "captured"} and (
            (amount is not None and Decimal(amount) != Decimal(row["amount"]))
            or (currency is not None and currency != row["currency"])
        ):
            status, failure, outcome = "failed", "amount_mismatch", "mismatch"
        try:
            async with self.session.begin_nested():
                await self.session.execute(
                    text(
                        """
                        update booking_payments
                        set status = cast(:s as text),
                            payment_ref = coalesce(cast(:pr as text), payment_ref),
                            instrument = coalesce(cast(:i as text), instrument),
                            failure_code = cast(:f as text),
                            authorized_at = case when cast(:s as text) = 'authorized'
                                                 then now() else authorized_at end,
                            captured_at = case when cast(:s as text) = 'captured'
                                               then now() else captured_at end
                        where id = :id
                        """
                    ),
                    {
                        "s": status,
                        "pr": payment_ref,
                        "i": instrument,
                        "f": failure,
                        "id": row["id"],
                    },
                )
        except DBAPIError as exc:
            if "payment_overcollection" in str(exc):
                return "overcollection"
            raise
        return outcome

    async def expire_intent(self, payment_id: str) -> None:
        await self.session.execute(
            text(
                f"""
                update booking_payments set status = 'expired'
                where id = :id and status in {_OPEN}
                """
            ),
            {"id": payment_id},
        )

    async def list_stale_intents(self, after_seconds: int, limit: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                f"""
                select id, provider, order_ref, expires_at, (expires_at < now()) as is_expired
                from booking_payments
                where channel = 'gateway' and status in {_OPEN} and order_ref is not null
                  and updated_at < now() - make_interval(secs => :after)
                order by updated_at
                limit :limit
                """
            ),
            {"after": float(after_seconds), "limit": limit},
        )
        return [dict(r) for r in result.mappings().all()]

    async def touch_intent(self, payment_id: str) -> None:
        await self.session.execute(
            text("update booking_payments set updated_at = now() where id = :id"),
            {"id": payment_id},
        )

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
        data["normalized"] = _json(data["normalized"])
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

    # ------------------------------------------------------- provider accounts
    async def apply_account_update(
        self, provider: str, account_ref: str, onboarding_status: str | None
    ) -> str:
        if onboarding_status is None:
            return "ignored"
        result = await self.session.execute(
            text(
                """
                update payment_provider_accounts set onboarding_status = :s
                where provider = :p and provider_account_ref = :a returning id
                """
            ),
            {"p": provider, "a": account_ref, "s": onboarding_status},
        )
        return "applied" if result.first() is not None else "unmatched"

    async def find_owner_salon_id(self, actor_id: str) -> str | None:
        """Read-only: never provisions a salon."""

        result = await self.session.execute(
            text(
                """
                select id from salons where owner_id = :a and is_active
                order by created_at limit 1
                """
            ),
            {"a": actor_id},
        )
        row = result.first()
        return str(row[0]) if row else None

    async def get_provider_account(self, salon_id: str, provider: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                select provider_account_ref, onboarding_status, requirements
                from payment_provider_accounts where salon_id = :s and provider = :p
                """
            ),
            {"s": salon_id, "p": provider},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        data = dict(row)
        data["requirements"] = _json(data["requirements"]) or []
        return data

    async def upsert_provider_account(
        self,
        salon_id: str,
        provider: str,
        account_ref: str,
        onboarding_status: str,
        requirements: list[str],
        actor_id: str,
    ) -> None:
        await self.session.execute(
            text(
                """
                insert into payment_provider_accounts
                  (salon_id, provider, provider_account_ref, onboarding_status,
                   requirements, created_by, updated_by)
                values (:s, :p, :a, :st, cast(:r as jsonb), :actor, :actor)
                on conflict (salon_id, provider) do update set
                  provider_account_ref = excluded.provider_account_ref,
                  onboarding_status = excluded.onboarding_status,
                  requirements = excluded.requirements
                """
            ),
            {
                "s": salon_id,
                "p": provider,
                "a": account_ref,
                "st": onboarding_status,
                "r": json.dumps(requirements),
                "actor": actor_id,
            },
        )

    async def get_payout_holder_name(self, salon_id: str) -> str | None:
        result = await self.session.execute(
            text("select account_holder_name from salon_payout_accounts where salon_id = :s"),
            {"s": salon_id},
        )
        row = result.first()
        return row[0] if row else None

    # --------------------------------------------------------------- earnings
    async def earnings(self, salon_id: str) -> dict[str, Any]:
        totals = (
            await self.session.execute(
                text(
                    f"""
                    select
                      coalesce(sum(amount) filter (
                        where channel = 'gateway' and status in {_SETTLED}), 0)
                        as online_collected,
                      coalesce(sum(platform_fee_amount) filter (
                        where channel = 'gateway' and status in {_SETTLED}), 0)
                        as platform_fees,
                      coalesce(sum(amount) filter (where channel = 'manual'), 0)
                        as manual_recorded,
                      count(*) filter (
                        where channel = 'gateway' and status in {_SETTLED}) as online_count,
                      count(*) filter (where channel = 'manual') as manual_count
                    from booking_payments where salon_id = :s
                    """
                ),
                {"s": salon_id},
            )
        ).mappings().one()
        refunded = (
            await self.session.execute(
                text(
                    """
                    select coalesce(sum(r.amount), 0)
                    from payment_refunds r join booking_payments p on p.id = r.payment_id
                    where p.salon_id = :s and r.status = 'processed'
                    """
                ),
                {"s": salon_id},
            )
        ).scalar_one()
        return {**dict(totals), "online_refunded": Decimal(refunded)}
