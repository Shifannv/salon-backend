"""Booking cancellation and closure-refund statements."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.account_deletion.constants import *
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)


class _BookingMixin:
    session: AsyncSession

    # ------------------------------------------------------- cancel and refund
    async def cancel_open_bookings(self, user_id: str) -> dict[str, int]:
        """Cancel every future pending/confirmed booking at the owner's salons and tell
        each customer, in ONE transaction, so a retry can neither skip nor repeat a notice.

        Also resolves every open booking-action request at those salons and cancels
        never-attempted checkout intents. Returns counts; a re-run finds nothing to do.
        """

        s = self.session
        params = {"uid": user_id}
        try:
            # Same transaction: stop future subscription renewal, expire unpaid subscription
            # orders locally and flag paid-but-unused periods BEFORE anything is erased.
            await SubscriptionBillingRepository(s).wind_down_salons(user_id)
            rows = (await s.execute(
                text(f"""
                    select id from bookings
                    where salon_id in ({_OWNED_SALONS})
                      and status in ('pending', 'confirmed') and end_datetime > now()
                    order by id for update
                """),
                params,
            )).all()
            ids = [str(r[0]) for r in rows]
            notified = 0
            if ids:
                await s.execute(
                    text("""
                        update bookings
                        set status = 'cancelled', cancellation_reason = :reason
                        where id = any(cast(:ids as uuid[]))
                    """),
                    {"ids": ids, "reason": SALON_CLOSED_REASON},
                )
                await s.execute(
                    text("""
                        update booking_payments set status = 'cancelled'
                        where booking_id = any(cast(:ids as uuid[]))
                          and channel = 'gateway' and status = 'created'
                    """),
                    {"ids": ids},
                )
                notified = (await s.execute(
                    text("""
                        with created as (
                          insert into notifications (user_id, booking_id, type, title, body, data)
                          select b.customer_id, b.id, 'booking_cancelled', 'Booking cancelled',
                                 cast(:base as text)
                                 || case when exists (
                                      select 1 from booking_payments p
                                      where p.booking_id = b.id and p.channel = 'gateway'
                                        and p.status in ('captured', 'partially_refunded'))
                                    then cast(:online as text) else '' end
                                 || case when exists (
                                      select 1 from booking_payments p
                                      where p.booking_id = b.id and p.channel = 'manual'
                                        and p.status = 'captured' and p.amount > 0)
                                    then cast(:manual as text) else '' end,
                                 jsonb_build_object('reason', cast(:reason as text))
                          from bookings b
                          where b.id = any(cast(:ids as uuid[])) and b.customer_id is not null
                          returning id, user_id
                        ), queued as (
                          insert into notification_outbox (notification_id, user_id)
                          select id, user_id from created
                          returning 1
                        )
                        select count(*) from queued
                    """),
                    {"ids": ids, "base": CLOSURE_NOTICE_BASE, "online": CLOSURE_NOTICE_ONLINE,
                     "manual": CLOSURE_NOTICE_MANUAL, "reason": SALON_CLOSED_REASON},
                )).scalar_one()
            resolved = (await s.execute(
                text(f"""
                    update booking_action_requests
                    set status = 'resolved', decision = 'invalidated',
                        decision_reason = 'Salon closed', resolved_at = now()
                    where status = 'pending'
                      and booking_id in (select id from bookings where salon_id in ({_OWNED_SALONS}))
                """),
                params,
            )).rowcount
            await s.commit()
            return {"cancelled": len(ids), "notified": int(notified), "resolved": int(resolved or 0)}
        except BaseException:
            await s.rollback()
            raise

    async def list_closure_refund_candidates(self, user_id: str) -> list[dict[str, Any]]:
        """Online payments on closure-cancelled bookings, with any refund already begun."""

        result = await self.session.execute(
            text(f"""
                select p.id as payment_id, p.booking_id, p.provider, p.payment_ref, p.amount,
                       p.status as payment_status,
                       coalesce((select sum(r.amount) from payment_refunds r
                                 where r.payment_id = p.id and r.status <> 'failed'
                                   and r.idempotency_key <> :key), 0) as other_refunded,
                       c.id as refund_id, c.status as refund_status, c.refund_ref
                from booking_payments p
                join bookings b on b.id = p.booking_id
                left join payment_refunds c
                  on c.payment_id = p.id and c.idempotency_key = :key
                where b.salon_id in ({_OWNED_SALONS})
                  and b.status = 'cancelled' and b.cancellation_reason = :reason
                  and p.channel = 'gateway' and p.payment_ref is not null
                  and (p.status in ('captured', 'partially_refunded') or c.id is not null)
                order by p.created_at, p.id
            """),
            {"uid": user_id, "key": CLOSURE_REFUND_KEY, "reason": SALON_CLOSED_REASON},
        )
        return [dict(r) for r in result.mappings().all()]

    async def begin_closure_refund(
        self, payment_id: str, booking_id: str, provider: str | None, amount: Any
    ) -> dict[str, Any]:
        """Insert the refund row (or return the existing one) BEFORE calling the provider.

        ``unique (payment_id, idempotency_key)`` makes this exactly-once per payment.
        """

        s = self.session
        try:
            await s.execute(
                text("""
                    insert into payment_refunds
                      (payment_id, booking_id, provider, amount, status, reason, idempotency_key)
                    values (:p, :b, :provider, :amount, 'created', :reason, :key)
                    on conflict (payment_id, idempotency_key) do nothing
                """),
                {"p": payment_id, "b": booking_id, "provider": provider, "amount": amount,
                 "reason": SALON_CLOSED_REASON, "key": CLOSURE_REFUND_KEY},
            )
            row = (await s.execute(
                text("""
                    select id, status, refund_ref, amount from payment_refunds
                    where payment_id = :p and idempotency_key = :key
                """),
                {"p": payment_id, "key": CLOSURE_REFUND_KEY},
            )).mappings().one()
            await s.commit()
            return dict(row)
        except BaseException:
            await s.rollback()
            raise

    async def finish_closure_refund(
        self, refund_id: str, refund_ref: str | None, status: str, failure_code: str | None
    ) -> None:
        try:
            await self.session.execute(
                text("""
                    update payment_refunds
                    set refund_ref = :ref, status = :status, failure_code = :code,
                        processed_at = case when :status = 'processed' then now() else processed_at end
                    where id = :id and status = 'created'
                """),
                {"id": refund_id, "ref": refund_ref, "status": status,
                 "code": failure_code[:120] if failure_code else None},
            )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise

    async def record_failed_closure_refund(
        self, payment_id: str, booking_id: str, provider: str | None, amount: Any, failure_code: str
    ) -> None:
        """Operator-visible record of a refund the platform could not issue."""

        try:
            await self.session.execute(
                text("""
                    insert into payment_refunds
                      (payment_id, booking_id, provider, amount, status, reason,
                       idempotency_key, failure_code)
                    values (:p, :b, :provider, :amount, 'failed', :reason, :key, :code)
                    on conflict (payment_id, idempotency_key) do update
                      set status = 'failed', failure_code = excluded.failure_code
                      where payment_refunds.status = 'created'
                        and payment_refunds.refund_ref is null
                """),
                {"p": payment_id, "b": booking_id, "provider": provider, "amount": amount,
                 "reason": SALON_CLOSED_REASON, "key": CLOSURE_REFUND_KEY,
                 "code": failure_code[:120]},
            )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise

    async def list_unsettled_closure_refunds(self, user_id: str) -> list[str]:
        result = await self.session.execute(
            text(f"""
                select r.id from payment_refunds r
                join bookings b on b.id = r.booking_id
                where b.salon_id in ({_OWNED_SALONS})
                  and r.idempotency_key = :key and r.status = 'created'
                order by r.created_at, r.id
            """),
            {"uid": user_id, "key": CLOSURE_REFUND_KEY},
        )
        return [str(r[0]) for r in result.all()]
