"""Owner earnings."""

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.payments._sql import _SETTLED


class EarningsMixin:
    """Earnings summary."""

    session: AsyncSession

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
