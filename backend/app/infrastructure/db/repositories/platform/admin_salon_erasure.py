"""Admin salon erasure: what a salon still owes, closing it, refunds, and the erase itself.

The deletion of rows is the database function ``erase_salon`` (migration 0058); everything here is the
scoped reads and writes around it. All statements are scoped to ONE salon, unlike the owner
account-deletion mixins, which are scoped to an owner's salons.
"""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.account_deletion.constants import (
    CLOSURE_NOTICE_BASE,
    CLOSURE_NOTICE_MANUAL,
    CLOSURE_NOTICE_ONLINE,
    CLOSURE_REFUND_KEY,
    SALON_CLOSED_REASON,
)
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)

_OPEN = "('pending', 'confirmed', 'checked_in')"
_ERASURE_TABLES = (
    "payout_audit", "salon_payout_payments", "salon_payout_corrections", "salon_payout_requests", "payout_proofs",
    "booking_finance_commands", "booking_policy_refund_jobs", "booking_finance_reconciliations",
    "booking_financial_outcomes", "booking_customer_changes", "staff_earnings", "booking_service_staff",
    "staff_commission_rule_versions", "payment_refunds", "payment_anomalies", "booking_payments",
    "booking_action_requests", "booking_audit_events", "booking_services", "bookings", "salon_expenses",
    "salon_cash_adjustments", "salon_day_closes", "salon_expense_rules", "support_erasure_events",
    "support_messages", "support_tickets", "subscription_events", "subscription_billing_records",
    "salon_subscriptions", "subscription_provider_accounts", "payment_provider_account_audit",
    "payment_provider_accounts", "salon_reports", "staff_services", "services", "staff", "salons",
    "account_deletion_requests", "booking_segments", "salon_service_categories",
)
# A payment still owed back to the customer: online, taken, not fully refunded, on a booking that is
# still open or was cancelled because the salon is closing.
_REFUND_SCOPE = f"""
    b.salon_id = :s and p.channel = 'gateway' and p.payment_ref is not null
    and p.status in ('authorized', 'captured', 'partially_refunded')
    and (b.status in {_OPEN} or (b.status = 'cancelled' and b.cancellation_reason = :closed))
"""
_REFUNDED = """coalesce((select sum(r.amount) from payment_refunds r
                          where r.payment_id = p.id and r.status <> 'failed'), 0)"""


class AdminSalonErasureMixin:
    session: AsyncSession

    async def erasure_figures(self, salon_id: str) -> dict[str, int] | None:
        """Everything a salon still owes or is owed, in whole paise. None when the salon is gone."""

        row = (await self.session.execute(
            text(f"""
                select
                  (select count(*) from salons where id = :s) as present,
                  (select count(*) from bookings where salon_id = :s and status in {_OPEN}) as open_bookings,
                  (select count(*) from booking_payments where salon_id = :s and channel = 'gateway'
                     and status in ('created', 'authorized')) as payments_pending_count,
                  (select count(*) from booking_payments p join bookings b on b.id = p.booking_id
                    where {_REFUND_SCOPE} and p.amount - {_REFUNDED} > 0) as refunds_due_count,
                  (select coalesce(sum(round((p.amount - {_REFUNDED}) * 100)), 0)::bigint
                     from booking_payments p join bookings b on b.id = p.booking_id
                    where {_REFUND_SCOPE} and p.amount - {_REFUNDED} > 0) as refunds_due_paise,
                  ((select count(*) from payment_refunds r join bookings b on b.id = r.booking_id
                     where b.salon_id = :s and r.status = 'created')
                   + (select count(*) from booking_policy_refund_jobs j join bookings b on b.id = j.booking_id
                       where b.salon_id = :s and j.status <> 'processed')) as refunds_pending_count,
                  (select count(*) from salon_payout_requests where salon_id = :s and status = 'requested')
                     as payout_requests_pending
            """),
            {"s": salon_id, "closed": SALON_CLOSED_REASON},
        )).mappings().one()
        if not row["present"]:
            return None
        return {key: int(value) for key, value in row.items() if key != "present"}

    async def lock_salon_for_erasure(self, salon_id: str) -> None:
        """Serialise two admins working on the same salon."""

        from sqlalchemy.exc import DBAPIError

        from app.core.exceptions import ConflictError

        await self.session.execute(text("select set_config('lock_timeout', '5s', true)"))
        # erase_salon disables DELETE triggers, requiring these table locks anyway.
        # Take them BEFORE row locks/readiness. NOWAIT avoids a lock cycle with an
        # already-active multi-table writer: rollback and let the admin retry instead.
        tables = ", ".join(f"public.{name}" for name in sorted(_ERASURE_TABLES))
        try:
            await self.session.execute(text(f"lock table {tables} in exclusive mode nowait"))
        except DBAPIError as exc:
            await self.session.rollback()
            if getattr(exc.orig, "sqlstate", None) == "55P03":
                raise ConflictError("The salon is being updated. Try permanent deletion again.") from exc
            raise
        # Ordinary reads continue; writers and SELECT FOR UPDATE wait until commit.
        await self.session.execute(text("select id from salons where id = :s for update"), {"s": salon_id})

    async def erasure_job(self, salon_id: str) -> dict[str, Any] | None:
        row = (await self.session.execute(
            text("select salon_id, status, media_keys, auth_user_ids from salon_erasure_jobs where salon_id = :s"),
            {"s": salon_id},
        )).mappings().first()
        return dict(row) if row else None

    # ----------------------------------------------------------------- closing
    async def close_salon_for_erasure(self, salon_id: str) -> dict[str, int]:
        """Hide the salon from customers, cancel its open bookings and tell each customer.

        One transaction, safe to repeat: a second run finds nothing left to cancel.
        """

        s = self.session
        params = {"s": salon_id}
        try:
            await s.execute(text("update salons set is_active = false where id = :s"), params)
            await self._stop_salon_billing(salon_id)
            ids = [str(r[0]) for r in (await s.execute(
                text(f"select id from bookings where salon_id = :s and status in {_OPEN} order by id for update"),
                params,
            )).all()]
            notified = 0
            if ids:
                await s.execute(
                    text("update bookings set status = 'cancelled', cancellation_reason = :reason "
                         "where id = any(cast(:ids as uuid[]))"),
                    {"ids": ids, "reason": SALON_CLOSED_REASON},
                )
                # Cancelling a booking does not cancel its provider order. Keep unresolved
                # intents until provider reconciliation confirms their financial outcome.
                notified = (await s.execute(
                    text("""
                        with created as (
                          insert into notifications (user_id, booking_id, type, title, body, data)
                          select b.customer_id, b.id, 'booking_cancelled', 'Booking cancelled',
                                 cast(:base as text)
                                 || case when exists (select 1 from booking_payments p where p.booking_id = b.id
                                      and p.channel = 'gateway' and p.status in ('captured', 'partially_refunded'))
                                    then cast(:online as text) else '' end
                                 || case when exists (select 1 from booking_payments p where p.booking_id = b.id
                                      and p.channel = 'manual' and p.status = 'captured' and p.amount > 0)
                                    then cast(:manual as text) else '' end,
                                 jsonb_build_object('reason', cast(:reason as text))
                          from bookings b where b.id = any(cast(:ids as uuid[])) and b.customer_id is not null
                          returning id, user_id
                        ), queued as (
                          insert into notification_outbox (notification_id, user_id)
                          select id, user_id from created returning 1
                        )
                        select count(*) from queued
                    """),
                    {"ids": ids, "base": CLOSURE_NOTICE_BASE, "online": CLOSURE_NOTICE_ONLINE,
                     "manual": CLOSURE_NOTICE_MANUAL, "reason": SALON_CLOSED_REASON},
                )).scalar_one()
            resolved = (await s.execute(
                text("""
                    update booking_action_requests
                    set status = 'resolved', decision = 'invalidated', decision_reason = 'Salon closed', resolved_at = now()
                    where status = 'pending' and booking_id in (select id from bookings where salon_id = :s)
                """),
                params,
            )).rowcount
            await s.commit()
            return {"cancelled": len(ids), "notified": int(notified), "resolved": int(resolved or 0)}
        except BaseException:
            await s.rollback()
            raise

    async def _stop_salon_billing(self, salon_id: str) -> None:
        """Stop renewal and expire unpaid subscription orders; the provider order itself cannot be cancelled."""

        await SubscriptionBillingRepository(self.session).cancel_renewal(salon_id)
        await self.session.execute(
            text("update subscription_billing_records set status = 'expired' "
                 "where salon_id = :s and status in ('created', 'authorized')"),
            {"s": salon_id},
        )

    # ----------------------------------------------------------------- refunds
    async def salon_refund_candidates(self, salon_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(f"""
                select p.id as payment_id, p.booking_id, p.provider, p.payment_ref, p.amount,
                       p.amount - {_REFUNDED} as remaining,
                       c.id as refund_id, c.status as refund_status, c.refund_ref
                from booking_payments p
                join bookings b on b.id = p.booking_id
                left join payment_refunds c on c.payment_id = p.id and c.idempotency_key = :key
                where {_REFUND_SCOPE} and p.amount - {_REFUNDED} > 0
                order by p.created_at, p.id
            """),
            {"s": salon_id, "closed": SALON_CLOSED_REASON, "key": CLOSURE_REFUND_KEY},
        )
        return [dict(r) for r in result.mappings().all()]

    async def record_salon_refund(
        self, payment_id: str, booking_id: str, provider: str | None, amount: Any, *,
        status: str = "created", refund_ref: str | None = None, failure_code: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert (or return) the closure refund row, once per payment (same key as the owner flow)."""

        s = self.session
        try:
            await s.execute(
                text("""
                    insert into payment_refunds
                      (payment_id, booking_id, provider, amount, status, reason, idempotency_key, kind,
                       refund_ref, failure_code, requested_by, processed_at)
                    values (:p, :b, :provider, :amount, :status, :reason, :key, 'closure',
                            :ref, :code, :actor, case when :status = 'processed' then now() end)
                    on conflict (payment_id, idempotency_key) do nothing
                """),
                {"p": payment_id, "b": booking_id, "provider": provider, "amount": amount, "status": status,
                 "reason": SALON_CLOSED_REASON, "key": CLOSURE_REFUND_KEY, "ref": refund_ref,
                 "code": failure_code[:120] if failure_code else None, "actor": actor_id},
            )
            row = (await s.execute(
                text("select id, status, refund_ref, amount from payment_refunds "
                     "where payment_id = :p and idempotency_key = :key"),
                {"p": payment_id, "key": CLOSURE_REFUND_KEY},
            )).mappings().one()
            await s.commit()
            return dict(row)
        except BaseException:
            await s.rollback()
            raise

    async def settle_salon_refund(
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

    async def mark_salon_refund_manual(self, refund_id: str) -> None:
        """The admin refunded this payment by hand. Never overwrites a reference the provider gave."""

        try:
            await self.session.execute(
                text("""
                    update payment_refunds
                    set status = 'processed', refund_ref = 'manual', failure_code = null, processed_at = now()
                    where id = :id and refund_ref is null and status in ('created', 'failed')
                """),
                {"id": refund_id},
            )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise

    async def reopen_failed_salon_refunds(self, salon_id: str) -> None:
        """Refunds the provider could not take go back to ``created`` so the admin can try again."""

        try:
            await self.session.execute(
                text("""
                    update payment_refunds set status = 'created', failure_code = null
                    where idempotency_key = :key and status = 'failed' and refund_ref is null
                      and booking_id in (select id from bookings where salon_id = :s)
                """),
                {"key": CLOSURE_REFUND_KEY, "s": salon_id},
            )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise

    # ----------------------------------------------------------------- erase
    async def erasure_footprint(self, salon_id: str) -> dict[str, Any]:
        """Everything the database erase removes but the outside world still holds: files and logins."""

        s = self.session
        params = {"s": salon_id}
        owner = (await s.execute(text(
            "select p.id from profiles p join salons s on s.owner_id = p.id "
            "where s.id = :s and p.role = 'owner'"
        ), params)).scalar_one_or_none()
        urls = (await s.execute(
            text("""
                select url from salon_images where salon_id = :s
                union select photo_url from staff where salon_id = :s
                union select photo_url from services where salon_id = :s
                union select qr_image_url from salons where id = :s
                union select avatar_url from profiles
                  where id = (select owner_id from salons where id = :s)
                     or id in (select profile_id from staff where salon_id = :s and profile_id is not null)
            """),
            params,
        )).scalars().all()
        staff_logins = [str(r) for r in (await s.execute(
            text("select p.id from profiles p join staff st on st.profile_id = p.id "
                 "where st.salon_id = :s and p.role = 'staff'"), params)).scalars().all()]
        return {"owner_id": str(owner) if owner else None, "media_urls": sorted(u for u in urls if u),
                "staff_profile_ids": staff_logins}

    async def erase_salon_rows(
        self, salon_id: str, media_urls: list[str], profile_ids: list[str], actor_id: str
    ) -> None:
        """Run the database erase and record what is left to clean outside it, in one transaction."""

        s = self.session
        try:
            await s.execute(text("select public.erase_salon(:s)"), {"s": salon_id})
            await s.execute(
                text("""
                    update salon_erasure_jobs
                    set status = 'cleanup_pending', media_keys = cast(:media as jsonb),
                        auth_user_ids = cast(:auth as jsonb), updated_at = now(),
                        step_state = step_state || jsonb_build_object('initiated_by', cast(:actor as text))
                    where salon_id = :s
                """),
                {"s": salon_id, "media": json.dumps(media_urls), "auth": json.dumps(profile_ids), "actor": actor_id},
            )
            await s.commit()
        except BaseException:
            await s.rollback()
            raise

    async def finish_erasure_job(self, salon_id: str) -> None:
        await self.session.execute(
            text("update salon_erasure_jobs set status = 'complete', media_keys = '[]'::jsonb, "
                 "auth_user_ids = '[]'::jsonb, completed_at = now(), updated_at = now() where salon_id = :s"),
            {"s": salon_id},
        )
        await self.session.commit()

    async def erase_orphan_profiles(self, profile_ids: list[str]) -> list[str]:
        """Delete the logins of staff and owner who no longer belong to any salon; return those removed."""

        removed: list[str] = []
        for profile_id in profile_ids:
            try:
                role = (await self.session.execute(
                    text("select role::text from profiles where id = :u for update"),
                    {"u": profile_id},
                )).scalar_one_or_none()
                if role is not None and role not in {"owner", "staff"}:
                    await self.session.rollback()
                    continue
                belongs = (await self.session.execute(
                    text("""
                        select exists (select 1 from salons where owner_id = :u)
                            or exists (select 1 from staff where profile_id = :u)
                            or exists (select 1 from bookings where customer_id = :u)
                    """),
                    {"u": profile_id},
                )).scalar_one()
                if belongs:
                    continue
                await self.session.execute(text("select set_config('app.account_erasure', 'on', true)"))
                await self.session.execute(text("delete from notifications where user_id = :u"), {"u": profile_id})
                await self.session.execute(text("delete from device_tokens where user_id = :u"), {"u": profile_id})
                await self.session.execute(text("select erase_profile_references(:u)"), {"u": profile_id})
                await self.session.execute(text("delete from profiles where id = :u"), {"u": profile_id})
                await self.session.commit()
                removed.append(profile_id)
            except BaseException:
                await self.session.rollback()
                raise
        return removed
