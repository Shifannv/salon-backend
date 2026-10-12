"""Raw-SQL repository for the payment ledger, refunds, webhook intake and idempotency.

Kept apart from ``platform_repository.py`` on purpose. Amounts are only ever read here
(``bookings.total_price`` / ``deposit_amount`` were computed in SQL); nothing recomputes
a price. Booking-level payment columns are written solely by the database's
``recompute_booking_payment_state`` trigger path.
"""

import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IdempotencyInProgressError, IdempotencyKeyReuseError
from app.infrastructure.db.session import set_actor_context

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

    async def set_actor(self, actor_id: str) -> None:
        """Re-arm the audit actor: ``set_config(..., true)`` dies with each commit."""

        await set_actor_context(self.session, actor_id)

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
        created_at, order_ref, payment_ref, intent_reference, platform_fee_amount,
        platform_commission_amount, commission_rate_percent, commission_base,
        commission_policy_version, overcollected_amount, provider_order_confirmed_at,
        payer_id
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

    async def commission_allocated(self, booking_id: str) -> Decimal:
        """Net commission already snapshotted on this booking's live online payments."""

        result = await self.session.execute(
            text(
                """
                select coalesce(sum(p.platform_commission_amount), 0)
                       - coalesce((select sum(r.commission_reversal_amount)
                                   from payment_refunds r
                                   join booking_payments q on q.id = r.payment_id
                                   where q.booking_id = :b and q.channel = 'gateway'
                                     and r.status = 'processed'), 0)
                from booking_payments p
                where p.booking_id = :b and p.channel = 'gateway'
                  and p.status in ('created', 'authorized', 'captured',
                                   'partially_refunded', 'refunded')
                """
            ),
            {"b": booking_id},
        )
        return Decimal(result.scalar_one())

    async def insert_intent(
        self,
        *,
        booking: dict[str, Any],
        actor_id: str,
        purpose: str,
        amount: Decimal,
        commission_amount: Decimal,
        commission_rate_percent: Decimal,
        commission_base: str,
        commission_policy_version: str,
        provider: str,
        settlement_model: str,
        intent_reference: str,
        order_ref: str | None,
        expires_in_seconds: int,
    ) -> str:
        """Persist the operation identity BEFORE the provider is called.

        The commission is a snapshot: rate, base, amount and policy version are written here
        once and never recomputed (a database trigger forbids changing them).
        """

        result = await self.session.execute(
            text(
                """
                insert into booking_payments
                  (booking_id, salon_id, payer_id, recorded_by, channel, purpose,
                   settlement_model, provider, amount, platform_fee_amount,
                   platform_commission_amount, commission_rate_percent, commission_base,
                   commission_policy_version, currency, status, intent_reference, order_ref,
                   expires_at)
                values (:booking_id, :salon_id, :actor, :actor, 'gateway', :purpose,
                        :settlement, :provider, :amount, :commission, :commission, :rate, :base,
                        :version, :currency, 'created', :ref, :order_ref,
                        now() + make_interval(secs => :ttl))
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
                "commission": commission_amount,
                "rate": commission_rate_percent,
                "base": commission_base,
                "version": commission_policy_version,
                "currency": booking["currency"],
                "ref": intent_reference,
                "order_ref": order_ref,
                "ttl": float(expires_in_seconds),
            },
        )
        return str(result.scalar_one())

    async def confirm_intent_order(self, payment_id: str, order_ref: str) -> None:
        """The provider acknowledged the order (the crash-safety marker)."""

        await self.session.execute(
            text(
                """
                update booking_payments
                set order_ref = coalesce(order_ref, cast(:o as text)),
                    provider_order_confirmed_at = now()
                where id = :id
                """
            ),
            {"o": order_ref, "id": payment_id},
        )

    async def fail_intent(self, payment_id: str, failure_code: str) -> None:
        await self.session.execute(
            text(
                f"""
                update booking_payments set status = 'failed', failure_code = :f
                where id = :id and status in {_OPEN} and provider_order_confirmed_at is null
                """
            ),
            {"f": failure_code[:120], "id": payment_id},
        )

    async def get_resumable_intent(self, booking_id: str) -> dict[str, Any] | None:
        """An open intent the provider never acknowledged (a crash/timeout left it behind)."""

        result = await self.session.execute(
            text(
                f"""
                select {self._PAYMENT_COLUMNS} from booking_payments
                where booking_id = :b and channel = 'gateway' and status = 'created'
                  and provider_order_confirmed_at is null and expires_at > now()
                limit 1
                """
            ),
            {"b": booking_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

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
                select id, payment_id, amount, status, reason, created_at, processed_at,
                       applies_to_excess
                from payment_refunds where booking_id = :b order by created_at, id
                """
            ),
            {"b": booking_id},
        )
        return [dict(r) for r in result.mappings().all()]

    # ---------------------------------------------------------------- refunds
    async def refund_totals(self, payment_id: str) -> dict[str, Decimal]:
        """Non-failed refund sums for one payment, split by kind."""

        row = (
            await self.session.execute(
                text(
                    """
                    select
                      coalesce(sum(amount) filter (where not applies_to_excess), 0) as regular,
                      coalesce(sum(amount) filter (where applies_to_excess), 0) as excess,
                      coalesce(sum(commission_reversal_amount), 0) as reversed
                    from payment_refunds where payment_id = :p and status <> 'failed'
                    """
                ),
                {"p": payment_id},
            )
        ).mappings().one()
        return {k: Decimal(v) for k, v in dict(row).items()}

    async def insert_refund(
        self,
        *,
        payment: dict[str, Any],
        actor_id: str,
        amount: Decimal,
        reason: str | None,
        idempotency_key: str,
        commission_reversal: Decimal = Decimal("0.00"),
        applies_to_excess: bool = False,
        refund_id: str | None = None,
        refund_ref: str | None = None,
    ) -> str:
        """Persist the refund BEFORE the provider is called.

        ``refund_id`` is pre-generated so a deterministic provider refund id can be derived
        from it and stored in ``refund_ref`` in the same insert.
        """

        result = await self.session.execute(
            text(
                """
                insert into payment_refunds
                  (id, payment_id, booking_id, provider, refund_ref, amount, status, reason,
                   idempotency_key, requested_by, commission_reversal_amount, applies_to_excess)
                values (coalesce(cast(:id as uuid), gen_random_uuid()), :p, :b, :provider,
                        :ref, :amount, 'created', :reason, :k, :actor, :rev, :excess)
                returning id
                """
            ),
            {
                "id": refund_id,
                "p": payment["id"],
                "b": payment["booking_id"],
                "provider": payment["provider"],
                "ref": refund_ref,
                "amount": amount,
                "reason": reason,
                "k": idempotency_key,
                "actor": actor_id,
                "rev": commission_reversal,
                "excess": applies_to_excess,
            },
        )
        return str(result.scalar_one())

    async def update_refund(
        self, refund_id: str, refund_ref: str | None, status: str, failure_code: str | None
    ) -> None:
        await self.session.execute(
            text(
                """
                update payment_refunds
                set refund_ref = coalesce(cast(:r as text), refund_ref), status = :s,
                    failure_code = :f,
                    processed_at = case when :s = 'processed' then now() else processed_at end
                where id = :id and status = 'created'
                """
            ),
            {"r": refund_ref, "s": status, "f": failure_code, "id": refund_id},
        )

    async def list_open_refunds(self, after_seconds: int, limit: int) -> list[dict[str, Any]]:
        """Refunds still 'created' after a while: the provider outcome is unknown."""

        result = await self.session.execute(
            text(
                """
                select r.id, r.provider, r.refund_ref, r.amount, p.order_ref, p.payment_ref
                from payment_refunds r join booking_payments p on p.id = r.payment_id
                where r.status = 'created' and r.refund_ref is not null
                  and r.updated_at < now() - make_interval(secs => :after)
                order by r.updated_at limit :limit
                """
            ),
            {"after": float(after_seconds), "limit": limit},
        )
        return [dict(r) for r in result.mappings().all()]

    async def get_refund_by_key(self, payment_id: str, key: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                select id, status, refund_ref, amount, applies_to_excess
                from payment_refunds where payment_id = :p and idempotency_key = :k
                """
            ),
            {"p": payment_id, "k": key},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def find_salon_by_account(self, provider: str, account_ref: str) -> str | None:
        result = await self.session.execute(
            text(
                """
                select salon_id from payment_provider_accounts
                where provider = :p and provider_account_ref = :a
                """
            ),
            {"p": provider, "a": account_ref},
        )
        row = result.first()
        return str(row[0]) if row else None

    async def touch_refund(self, refund_id: str) -> None:
        await self.session.execute(
            text("update payment_refunds set updated_at = now() where id = :id"),
            {"id": refund_id},
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

    # ------------------------------------------------------------- anomalies
    async def record_anomaly(
        self,
        *,
        kind: str,
        provider: str | None,
        provider_ref: str | None,
        salon_id: str | None = None,
        booking_id: str | None = None,
        payment_id: str | None = None,
        amount: Decimal | None = None,
        detail: str | None = None,
    ) -> None:
        """Operator-visible row. Deduplicated by (kind, provider, provider_ref)."""

        await self.session.execute(
            text(
                """
                insert into payment_anomalies
                  (kind, provider, provider_ref, salon_id, booking_id, payment_id, amount, detail)
                values (:k, :p, :r, :s, :b, :pay, :a, :d)
                on conflict (kind, provider, provider_ref) do nothing
                """
            ),
            {
                "k": kind, "p": provider, "r": provider_ref, "s": salon_id, "b": booking_id,
                "pay": payment_id, "a": amount, "d": (detail or "")[:300] or None,
            },
        )

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

        Shared by webhooks, the client callback, status refresh and reconciliation. Returns
        ``applied``, ``ignored`` (stale or out of order), ``unmatched``, ``mismatch`` (amount or
        currency differs; the row is failed, an anomaly is recorded, the booking is never marked
        paid), ``overcollected`` (money really moved but the booking was owed less: the capture
        is RECORDED with the excess, the booking is not marked paid twice, an anomaly is
        recorded) or ``overcollection`` (last-resort database guard fired).

        Lock order is booking then payment, the same as the request paths, so a concurrent cash
        receipt and an online capture serialise on the booking row.
        """

        from app.domain.entities.payment import is_forward_transition

        located = (
            await self.session.execute(
                text(
                    """
                    select id, booking_id from booking_payments
                    where provider = :p and channel = 'gateway'
                      and ((cast(:o as text) is not null and order_ref = cast(:o as text))
                        or (cast(:pr as text) is not null and payment_ref = cast(:pr as text)))
                    limit 1
                    """
                ),
                {"p": provider, "o": order_ref, "pr": payment_ref},
            )
        ).mappings().one_or_none()
        if located is None:
            return "unmatched"
        booking = (
            await self.session.execute(
                text("select total_price from bookings where id = :b for update"),
                {"b": located["booking_id"]},
            )
        ).mappings().one_or_none()
        row = (
            await self.session.execute(
                text(
                    """
                    select id, booking_id, salon_id, status, amount, currency
                    from booking_payments where id = :id for update
                    """
                ),
                {"id": located["id"]},
            )
        ).mappings().one_or_none()
        if row is None or booking is None:
            return "unmatched"
        if not is_forward_transition(row["status"], status):
            return "ignored"
        outcome = "applied"
        failure = failure_code
        excess = Decimal("0.00")
        if status in {"authorized", "captured"} and (
            (amount is not None and Decimal(amount) != Decimal(row["amount"]))
            or (currency is not None and currency != row["currency"])
        ):
            status, failure, outcome = "failed", "amount_mismatch", "mismatch"
        elif status == "captured":
            owed = await self._owed(str(row["booking_id"]), Decimal(booking["total_price"]))
            excess = max(Decimal(row["amount"]) - owed, Decimal("0.00"))
            if excess > 0:
                outcome = "overcollected"
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
                            overcollected_amount = case when cast(:s as text) = 'captured'
                                then cast(:x as numeric) else overcollected_amount end,
                            authorized_at = case when cast(:s as text) = 'authorized'
                                                 then now() else authorized_at end,
                            captured_at = case when cast(:s as text) = 'captured'
                                               then now() else captured_at end
                        where id = :id
                        """
                    ),
                    {
                        "s": status, "pr": payment_ref, "i": instrument, "f": failure,
                        "x": excess, "id": row["id"],
                    },
                )
        except DBAPIError as exc:
            if "payment_overcollection" in str(exc):
                return "overcollection"
            raise
        if outcome in {"mismatch", "overcollected"}:
            await self.record_anomaly(
                kind="amount_mismatch" if outcome == "mismatch" else "overcollection",
                provider=provider,
                provider_ref=str(row["id"]),
                salon_id=str(row["salon_id"]),
                booking_id=str(row["booking_id"]),
                payment_id=str(row["id"]),
                amount=excess if outcome == "overcollected" else amount,
                detail=(
                    "captured amount differs from the ledger row"
                    if outcome == "mismatch"
                    else "capture exceeds what the booking was owed; refund the excess"
                ),
            )
        return outcome

    async def _owed(self, booking_id: str, total: Decimal) -> Decimal:
        """What the booking still owes (caller holds the booking lock)."""

        value = (
            await self.session.execute(
                text(
                    """
                    select
                      coalesce((select sum(amount - overcollected_amount) from booking_payments
                                where booking_id = :b
                                  and status in ('captured', 'partially_refunded', 'refunded')), 0)
                      - coalesce((select sum(amount) from payment_refunds
                                  where booking_id = :b and status = 'processed'
                                    and not applies_to_excess), 0)
                    """
                ),
                {"b": booking_id},
            )
        ).scalar_one()
        return max(Decimal(total) - Decimal(value), Decimal("0.00"))

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
        old = (
            await self.session.execute(
                text(
                    """
                    select salon_id, onboarding_status from payment_provider_accounts
                    where provider = :p and provider_account_ref = :a for update
                    """
                ),
                {"p": provider, "a": account_ref},
            )
        ).mappings().one_or_none()
        if old is None:
            return "unmatched"
        if old["onboarding_status"] == onboarding_status:
            return "ignored"
        await self.session.execute(
            text(
                """
                update payment_provider_accounts set onboarding_status = :s
                where provider = :p and provider_account_ref = :a
                """
            ),
            {"p": provider, "a": account_ref, "s": onboarding_status},
        )
        await self.add_account_audit(
            salon_id=str(old["salon_id"]), provider=provider, action="status_changed",
            previous_status=old["onboarding_status"], new_status=onboarding_status,
            vendor_ref=account_ref, actor_id=None,
        )
        return "applied"

    async def add_account_audit(
        self,
        *,
        salon_id: str,
        provider: str,
        action: str,
        previous_status: str | None,
        new_status: str | None,
        vendor_ref: str | None,
        actor_id: str | None,
        detail: str | None = None,
    ) -> None:
        """Append-only registration trail. References and statuses only, never KYC data."""

        await self.session.execute(
            text(
                """
                insert into payment_provider_account_audit
                  (salon_id, provider, action, previous_status, new_status, vendor_ref,
                   actor_id, detail)
                values (:s, :p, :a, :ps, :ns, :v, :actor, :d)
                """
            ),
            {
                "s": salon_id, "p": provider, "a": action, "ps": previous_status,
                "ns": new_status, "v": vendor_ref, "actor": actor_id,
                "d": (detail or "")[:300] or None,
            },
        )

    async def begin_registration(
        self, salon_id: str, provider: str, actor_id: str, vendor_ref_for: Callable[[int], str]
    ) -> dict[str, Any]:
        """Persist the payee identity with status 'pending' BEFORE the provider call.

        A pending registration is retried under the same vendor id (idempotent at the
        provider). Re-registering from any other status starts a new generation, hence a new
        vendor id: bank details are never stored, so a change can only be a fresh submission.
        ``vendor_ref_for(generation)`` derives the id.
        """

        existing = (
            await self.session.execute(
                text(
                    """
                    select provider_account_ref, onboarding_status, registration_generation
                    from payment_provider_accounts
                    where salon_id = :s and provider = :p for update
                    """
                ),
                {"s": salon_id, "p": provider},
            )
        ).mappings().one_or_none()
        if existing is None:
            generation, action, previous = 1, "registered", None
        elif existing["onboarding_status"] == "pending" and existing["provider_account_ref"]:
            return {
                "vendor_ref": existing["provider_account_ref"],
                "generation": existing["registration_generation"],
                "previous_status": "pending",
            }
        else:
            generation = int(existing["registration_generation"]) + 1
            action, previous = "re_registered", existing["onboarding_status"]
        vendor_ref = vendor_ref_for(generation)
        await self.session.execute(
            text(
                """
                insert into payment_provider_accounts
                  (salon_id, provider, provider_account_ref, onboarding_status, requirements,
                   registration_generation, created_by, updated_by)
                values (:s, :p, :v, 'pending', cast('[]' as jsonb), :g, :actor, :actor)
                on conflict (salon_id, provider) do update set
                  provider_account_ref = excluded.provider_account_ref,
                  onboarding_status = 'pending', requirements = cast('[]' as jsonb),
                  registration_generation = excluded.registration_generation
                """
            ),
            {"s": salon_id, "p": provider, "v": vendor_ref, "g": generation, "actor": actor_id},
        )
        await self.add_account_audit(
            salon_id=salon_id, provider=provider, action=action, previous_status=previous,
            new_status="pending", vendor_ref=vendor_ref, actor_id=actor_id,
        )
        return {"vendor_ref": vendor_ref, "generation": generation, "previous_status": previous}

    async def set_account_result(
        self,
        salon_id: str,
        provider: str,
        status: str,
        requirements: list[str],
        actor_id: str,
        account_ref: str | None = None,
    ) -> None:
        await self.session.execute(
            text(
                """
                update payment_provider_accounts
                set onboarding_status = :st, requirements = cast(:r as jsonb), updated_by = :actor,
                    provider_account_ref = coalesce(cast(:ref as text), provider_account_ref)
                where salon_id = :s and provider = :p
                """
            ),
            {"s": salon_id, "p": provider, "st": status, "r": json.dumps(requirements),
             "actor": actor_id, "ref": account_ref},
        )

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
                select provider_account_ref, onboarding_status, requirements,
                       registration_generation
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
        """Ledger-derived totals. Commission comes from the immutable snapshot only."""

        totals = (
            await self.session.execute(
                text(
                    f"""
                    select
                      coalesce(sum(amount - overcollected_amount) filter (
                        where channel = 'gateway' and status in {_SETTLED}), 0)
                        as online_collected,
                      coalesce(sum(platform_commission_amount) filter (
                        where channel = 'gateway' and status in {_SETTLED}), 0)
                        as platform_fees,
                      coalesce(sum(overcollected_amount) filter (
                        where channel = 'gateway' and status in {_SETTLED}), 0)
                        as overcollected,
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
        refunds = (
            await self.session.execute(
                text(
                    """
                    select
                      coalesce(sum(r.amount) filter (where not r.applies_to_excess), 0) as refunded,
                      coalesce(sum(r.commission_reversal_amount), 0) as reversed
                    from payment_refunds r join booking_payments p on p.id = r.payment_id
                    where p.salon_id = :s and r.status = 'processed'
                    """
                ),
                {"s": salon_id},
            )
        ).mappings().one()
        return {
            **dict(totals),
            "online_refunded": Decimal(refunds["refunded"]),
            "commission_reversed": Decimal(refunds["reversed"]),
        }
