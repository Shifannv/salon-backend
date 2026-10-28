"""Anomalies and provider payment observations."""

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.payments._sql import _OPEN


class ObservationMixin:
    """Fold provider observations into the ledger."""

    session: AsyncSession

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
                select id, booking_id, salon_id, status, amount, currency, service_amount, online_processing_charge
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
            service = Decimal(row["service_amount"])
            excess = ((max(service - owed, Decimal("0")) * Decimal(row["amount"]) / service)
                      .quantize(Decimal("0.01"))) if service else Decimal("0")
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
                      coalesce((select sum(case when amount > 0 then round((amount - overcollected_amount) * service_amount / amount, 2) else 0 end) from booking_payments
                                where booking_id = :b
                                  and status in ('captured', 'partially_refunded', 'refunded')), 0)
                      - coalesce((select round(sum(case when p.amount > 0 then r.amount * p.service_amount / p.amount else 0 end), 2) from payment_refunds r join booking_payments p on p.id=r.payment_id
                                  where r.booking_id = :b and r.status = 'processed'
                                    and not r.applies_to_excess), 0)
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
