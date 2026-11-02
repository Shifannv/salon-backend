"""Booking locks and the payment-intent ledger."""

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.payments._sql import _OPEN
from app.infrastructure.db.rows import one_dict_or_none


class IntentMixin:
    """Booking reads and intent lifecycle."""

    session: AsyncSession

    # --------------------------------------------------------------- bookings
    async def lock_booking(self, booking_id: str, actor_id: str) -> dict[str, Any] | None:
        """Lock a booking and report the actor's relationship to it."""

        result = await self.session.execute(
            text(
                """
                select b.id, b.salon_id, b.customer_id, b.status, b.total_price, b.checkout_policy_version,
                       b.deposit_amount, b.paid_amount, b.refunded_amount, b.currency,
                       b.payment_status, b.payment_preference, s.owner_id,
                       (s.accepting_bookings and public.salon_booking_eligible(s.id)) as accepts_new_online_payment,
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
        return one_dict_or_none(result)

    async def read_booking(self, booking_id: str, actor_id: str) -> dict[str, Any] | None:
        """Same shape as ``lock_booking`` without locking (read endpoints)."""

        result = await self.session.execute(
            text(
                """
                select b.id, b.salon_id, b.customer_id, b.status, b.total_price, b.checkout_policy_version,
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
        return one_dict_or_none(result)

    # ----------------------------------------------------------------- ledger
    _PAYMENT_COLUMNS = """
        id, booking_id, salon_id, channel, purpose, settlement_model, provider, method,
        instrument, amount, currency, status, failure_code, expires_at, captured_at,
        created_at, order_ref, payment_ref, intent_reference, platform_fee_amount,
        platform_commission_amount, commission_rate_percent, commission_base,
        commission_policy_version, overcollected_amount, provider_order_confirmed_at,
        payer_id
        , collection_method, collected_by_owner, online_processing_charge, service_amount, provider_session_id
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
        return one_dict_or_none(result)

    async def commission_inputs(self, salon_id: str) -> dict[str, Any]:
        """What the super admin has set: the platform rate and base, and this salon's own rate."""

        result = await self.session.execute(
            text(
                """
                select s.commission_rate_percent as platform_rate, s.commission_base as platform_base,
                       s.policy_version,
                       (select o.commission_rate_percent from salon_commission_overrides o
                        where o.salon_id = cast(:salon as uuid)) as salon_rate
                from platform_payment_settings s where s.singleton
                """
            ),
            {"salon": salon_id},
        )
        row = result.mappings().first()
        return dict(row) if row else {
            "platform_rate": None, "platform_base": None, "policy_version": 1, "salon_rate": None,
        }

    async def booking_commission_policy(self, booking_id: str) -> dict[str, Any] | None:
        """The rate, base and version this booking's first live online payment was charged at."""

        result = await self.session.execute(
            text(
                """
                select commission_rate_percent, commission_base, commission_policy_version
                from booking_payments
                where booking_id = :b and channel = 'gateway'
                  and status in ('created', 'authorized', 'captured', 'partially_refunded', 'refunded')
                order by created_at, id limit 1
                """
            ),
            {"b": booking_id},
        )
        return one_dict_or_none(result)

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

    async def processing_charge_allocated(self, booking_id: str) -> Decimal:
        result = await self.session.execute(text("""
            select coalesce(sum(p.online_processing_charge),0) - coalesce((
              select round(sum(r.amount * q.online_processing_charge / nullif(q.amount,0)),2)
              from payment_refunds r join booking_payments q on q.id=r.payment_id
              where q.booking_id=:id and r.status='processed'),0)
            from booking_payments p where p.booking_id=:id and p.channel='gateway'
              and p.status in ('captured','partially_refunded','refunded')
        """), {"id":booking_id})
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
        online_processing_charge: Decimal = Decimal("0"),
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
                   settlement_model, provider, amount, online_processing_charge, platform_fee_amount,
                   platform_commission_amount, commission_rate_percent, commission_base,
                   commission_policy_version, currency, status, intent_reference, order_ref,
                   expires_at)
                values (:booking_id, :salon_id, :actor, :actor, 'gateway', :purpose,
                        :settlement, :provider, :amount, :processing, :commission, :commission, :rate, :base,
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
                "processing": online_processing_charge,
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

    async def confirm_intent_order(self, payment_id: str, order_ref: str, provider_session_id: str | None = None) -> None:
        """The provider acknowledged the order (the crash-safety marker)."""

        await self.session.execute(
            text(
                """
                update booking_payments
                set order_ref = coalesce(order_ref, cast(:o as text)),
                    provider_order_confirmed_at = now(),
                    provider_session_id = coalesce(provider_session_id, :session_id)
                where id = :id
                """
            ),
            {"o": order_ref, "id": payment_id, "session_id": provider_session_id},
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
        return one_dict_or_none(result)

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
        return one_dict_or_none(result)

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
        return one_dict_or_none(result)

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
        return one_dict_or_none(result)

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
