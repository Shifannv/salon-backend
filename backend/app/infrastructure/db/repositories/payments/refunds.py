"""Refund rows."""

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.rows import one_dict_or_none


class RefundMixin:
    """Refund persistence and observation."""

    session: AsyncSession

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
        return one_dict_or_none(result)

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
