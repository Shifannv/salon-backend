"""Raw-SQL repository for owner subscription billing (migration 0030).

Extends :class:`PaymentRepository` ONLY to reuse the DB-backed money idempotency table, the
anomaly log, the webhook intake helpers and commit/rollback; none of the booking-ledger
queries are used here. Amounts are read from ``subscription_plans`` INSIDE the insert, so the
purchase snapshot can never disagree with the plan row it was taken from.
"""

import hashlib
import json
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.db.repositories.payment_repository import PaymentRepository

_BILLING_COLUMNS = """
    id, salon_id, plan_id, plan_code, provider, receipt, provider_order_ref,
    provider_payment_ref, status, amount, currency, billing_interval, tax_amount,
    tax_inclusive, benefits, refunded_amount, period_start, period_end, subscription_id,
    expires_at, paid_at, applied_at, failure_code, created_by, created_at, updated_at
"""


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _row(mapping: Any) -> dict[str, Any]:
    row = dict(mapping)
    if "benefits" in row:
        row["benefits"] = _json(row["benefits"])
    if "features" in row:
        row["features"] = _json(row["features"])
    return row


class SubscriptionBillingRepository(PaymentRepository):
    async def booking_access(self, salon_id):
        row = (await self.session.execute(text("""
            select public.salon_booking_eligible(s.id) as eligible,
              a.trial_started_at,a.trial_ends_at,a.trial_booking_limit,a.bookings_counted,
              a.trial_limit_reached_at from salons s
              left join salon_access a on a.salon_id=s.id where s.id=:id
        """), {"id":salon_id})).mappings().one()
        return dict(row)

    # ---------------------------------------------------------------- plans
    async def list_purchasable_plans(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                select id, code, name, description, tier, ranking_weight, price_amount,
                       currency, billing_interval, features, tax_inclusive
                from subscription_plans
                where is_active and price_amount > 0
                  and billing_interval in ('monthly', 'quarterly', 'semiannual', 'yearly')
                order by tier asc, price_amount asc, code asc
                """
            )
        )
        return [_row(r) for r in result.mappings().all()]

    async def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                select id, code, name, tier, price_amount, currency, billing_interval,
                       features, is_active
                from subscription_plans where id = :id
                """
            ),
            {"id": plan_id},
        )
        row = result.mappings().one_or_none()
        return _row(row) if row else None

    # ------------------------------------------------------- subscriptions
    async def latest_subscription(self, salon_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                select ss.id, ss.salon_id, ss.plan_id, ss.status, ss.starts_at,
                       ss.current_period_start, ss.current_period_end, ss.cancelled_at,
                       ss.expires_at, ss.grace_period_end,
                       sp.code as plan_code, sp.name as plan_name, sp.tier as plan_tier,
                       sp.features as plan_features
                from salon_subscriptions ss
                join subscription_plans sp on sp.id = ss.plan_id
                where ss.salon_id = :s
                order by ss.created_at desc, ss.id desc limit 1
                """
            ),
            {"s": salon_id},
        )
        row = result.mappings().one_or_none()
        return _row(row) if row else None

    async def cancel_renewal(self, salon_id: str) -> str:
        result = await self.session.execute(
            text("select cancel_salon_subscription_renewal(:s)"), {"s": salon_id}
        )
        return str(result.scalar_one())

    async def sweep_lapsed(self) -> int:
        result = await self.session.execute(text("select sweep_lapsed_subscriptions()"))
        return int(result.scalar_one())

    # -------------------------------------------------------- billing rows
    async def insert_billing(
        self,
        *,
        salon_id: str,
        plan_id: str,
        provider: str,
        receipt: str,
        actor_id: str,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        """Persist the purchase (price snapshot included) BEFORE any provider call."""

        try:
            result = await self.session.execute(
                text(
                    f"""
                    insert into subscription_billing_records
                      (salon_id, plan_id, plan_code, provider, receipt, amount, currency,
                       billing_interval, tax_inclusive, benefits, expires_at, created_by)
                    select :s, p.id, p.code, :provider, :receipt, p.price_amount, p.currency,
                           p.billing_interval, p.tax_inclusive, p.features,
                           now() + make_interval(secs => :ttl), :actor
                    from subscription_plans p
                    where p.id = :plan and p.is_active and p.price_amount > 0
                    returning {_BILLING_COLUMNS}
                    """
                ),
                {
                    "s": salon_id, "plan": plan_id, "provider": provider, "receipt": receipt,
                    "ttl": float(ttl_seconds), "actor": actor_id,
                },
            )
        except IntegrityError as exc:
            await self.session.rollback()
            if "uq_subscription_billing_open_per_salon" in str(exc):
                raise ConflictError(
                    "A subscription payment is already open for this salon; finish it first"
                ) from exc
            raise
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subscription plan not found")
        return _row(row)

    async def _one(self, where: str, params: dict[str, Any], lock: bool = False) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                f"select {_BILLING_COLUMNS} from subscription_billing_records where {where}"
                + (" for update" if lock else "")
            ),
            params,
        )
        row = result.mappings().one_or_none()
        return _row(row) if row else None

    async def get_billing(self, billing_id: str, *, lock: bool = False) -> dict[str, Any] | None:
        return await self._one("id = :i", {"i": billing_id}, lock)

    async def get_open_billing(self, salon_id: str) -> dict[str, Any] | None:
        return await self._one(
            "salon_id = :s and status in ('created', 'authorized')", {"s": salon_id}
        )

    async def get_billing_by_order(self, provider: str, order_ref: str) -> dict[str, Any] | None:
        return await self._one(
            "provider = :p and provider_order_ref = :o", {"p": provider, "o": order_ref}
        )

    async def get_billing_by_payment(self, provider: str, payment_ref: str) -> dict[str, Any] | None:
        return await self._one(
            "provider = :p and provider_payment_ref = :r", {"p": provider, "r": payment_ref}
        )

    async def list_history(self, salon_id: str, limit: int, offset: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                f"""
                select {_BILLING_COLUMNS} from subscription_billing_records
                where salon_id = :s order by created_at desc, id desc
                limit :l offset :o
                """
            ),
            {"s": salon_id, "l": limit, "o": offset},
        )
        return [_row(r) for r in result.mappings().all()]

    async def set_order_ref(self, billing_id: str, order_ref: str) -> None:
        await self.session.execute(
            text(
                """
                update subscription_billing_records set provider_order_ref = :o
                where id = :i and (provider_order_ref is null or provider_order_ref = :o)
                """
            ),
            {"i": billing_id, "o": order_ref},
        )

    async def mark_paid(self, billing_id: str, payment_ref: str) -> bool:
        """Forward-only: failed/expired may still become paid (late capture is real money)."""

        result = await self.session.execute(
            text(
                """
                update subscription_billing_records
                set status = 'paid', provider_payment_ref = :p, failure_code = null,
                    paid_at = coalesce(paid_at, now())
                where id = :i and status in ('created', 'authorized', 'failed', 'expired')
                  and (provider_payment_ref is null or provider_payment_ref = :p)
                returning id
                """
            ),
            {"i": billing_id, "p": payment_ref},
        )
        return result.first() is not None

    async def note_failure(self, billing_id: str, code: str | None) -> None:
        """A failed ATTEMPT does not end an order (the payer may retry): only remember it."""

        await self.session.execute(
            text(
                """
                update subscription_billing_records set failure_code = :c
                where id = :i and status in ('created', 'authorized')
                """
            ),
            {"i": billing_id, "c": (code or "payment_failed")[:120]},
        )

    async def finish_unpaid(self, billing_id: str, status: str) -> bool:
        """Close an unpaid order as ``failed`` (an attempt failed) or ``expired``."""

        result = await self.session.execute(
            text(
                """
                update subscription_billing_records set status = :s
                where id = :i and status in ('created', 'authorized') returning id
                """
            ),
            {"i": billing_id, "s": status},
        )
        return result.first() is not None

    async def touch(self, billing_id: str) -> None:
        await self.session.execute(
            text("update subscription_billing_records set updated_at = now() where id = :i"),
            {"i": billing_id},
        )

    async def set_refunded(self, billing_id: str, refunded: Decimal) -> str | None:
        """Absolute, monotonic: duplicate or reordered refund events converge."""

        result = await self.session.execute(
            text(
                """
                update subscription_billing_records
                set refunded_amount = greatest(refunded_amount, least(:r, amount)),
                    status = case
                      when greatest(refunded_amount, least(:r, amount)) >= amount then 'refunded'
                      when greatest(refunded_amount, least(:r, amount)) > 0 then 'partially_refunded'
                      else status end
                where id = :i and status in ('paid', 'partially_refunded', 'refunded')
                returning status
                """
            ),
            {"i": billing_id, "r": refunded},
        )
        row = result.first()
        return str(row[0]) if row else None

    async def apply(self, billing_id: str, grace_days: int) -> str:
        """Atomic, idempotent activation (SQL function). Returns its outcome code."""

        result = await self.session.execute(
            text("select apply_subscription_billing_record(:i, :g)"),
            {"i": billing_id, "g": grace_days},
        )
        return str(result.scalar_one())

    async def list_stale_open(self, after_seconds: int, limit: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                f"""
                select {_BILLING_COLUMNS}, (expires_at <= now()) as is_expired
                from subscription_billing_records
                where status in ('created', 'authorized')
                  and updated_at < now() - make_interval(secs => :a)
                order by updated_at limit :l
                """
            ),
            {"a": float(after_seconds), "l": limit},
        )
        return [_row(r) for r in result.mappings().all()]

    async def list_unapplied_paid(self, limit: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                f"""
                select {_BILLING_COLUMNS} from subscription_billing_records
                where status in ('paid', 'partially_refunded') and applied_at is null
                order by updated_at limit :l
                """
            ),
            {"l": limit},
        )
        return [_row(r) for r in result.mappings().all()]

    # -------------------------------------------------------- domain event log
    async def log_event(
        self,
        *,
        subscription_id: str | None,
        provider: str,
        reference: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Record a normalised event in ``subscription_events`` (deduped per provider+ref)."""

        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        result = await self.session.execute(
            text(
                """
                insert into subscription_events
                  (salon_subscription_id, provider_name, provider_event_reference, event_type,
                   payload_hash, processing_status, processed_at)
                values (:s, :p, :r, :t, :h, 'processed', now())
                on conflict (provider_name, provider_event_reference)
                  where provider_name is not null and provider_event_reference is not null
                  do nothing
                returning id
                """
            ),
            {"s": subscription_id, "p": provider, "r": reference[:400], "t": event_type, "h": digest},
        )
        return result.first() is not None

    # --------------------------------------------------------- account closure
    async def wind_down_salons(self, owner_id: str) -> dict[str, int]:
        """Closure: cancel renewal, expire unpaid orders locally, flag paid-but-unused periods.

        Idempotent. The provider order itself cannot be cancelled (a late payment on it is
        recorded as an anomaly by the blocked-closed path, never activated).
        """

        params = {"uid": owner_id}
        owned = "select id from salons where owner_id = :uid"
        cancelled = 0
        for row in (await self.session.execute(text(f"{owned}"), params)).all():
            outcome = await self.cancel_renewal(str(row[0]))
            cancelled += 1 if outcome == "cancelled" else 0
        expired = await self.session.execute(
            text(
                f"""
                update subscription_billing_records set status = 'expired'
                where salon_id in ({owned}) and status in ('created', 'authorized') returning id
                """
            ),
            params,
        )
        expired_count = len(expired.all())
        unused = await self.session.execute(
            text(
                f"""
                insert into payment_anomalies (kind, provider, provider_ref, salon_id, amount, detail)
                select 'subscription_unused_period', b.provider, b.provider_payment_ref, b.salon_id,
                       b.amount - b.refunded_amount,
                       'salon closed with a paid period still running; refund decision needed'
                from subscription_billing_records b
                where b.salon_id in ({owned}) and b.status in ('paid', 'partially_refunded')
                  and b.period_end is not null and b.period_end > now()
                  and b.amount - b.refunded_amount > 0
                on conflict (kind, provider, provider_ref) do nothing
                returning id
                """
            ),
            params,
        )
        return {
            "renewals_cancelled": cancelled,
            "orders_expired": expired_count,
            "unused_periods_flagged": len(unused.all()),
        }

