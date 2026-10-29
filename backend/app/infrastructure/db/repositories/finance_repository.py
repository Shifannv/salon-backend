"""Owner finance cash book queries and append-only writes (0051). Money is integer paise.

Receipts, refunds and sales are READ from the existing payment tables; expenses, adjustments and
day closes are the only rows written here. Every write is idempotent per salon, and a repeat with
a different body is refused so a retried request can never record money twice.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IdempotencyKeyReuseError
from app.domain.entities.subscription import derive_entitlement
from app.domain.services.finance_ledger import TrialState, local_day_bounds
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)

_WRITABLE = frozenset({"salon_expenses", "salon_cash_adjustments", "salon_day_closes"})
_PAISE = "round({col} * 100)::bigint"
# Statuses that still count as money received: a refund moves a payment out of 'captured', but
# the receipt happened, and the refund is subtracted separately.
_RECEIVED = "('captured','partially_refunded','refunded')"

_DAY_SQL = text(
    f"""
    with sales as (
      select coalesce(sum({_PAISE.format(col='total_price')}), 0)::bigint as v
      from bookings
      where salon_id = :salon and status = 'completed'
        and completed_at >= :a and completed_at < :b
    ), received as (
      select coalesce(sum({_PAISE.format(col='amount')}) filter (where collection_method = 'CASH'), 0)::bigint as cash,
             coalesce(sum({_PAISE.format(col='amount')}) filter (where collection_method = 'UPI_DIRECT'), 0)::bigint as upi
      from booking_payments
      where salon_id = :salon and channel = 'manual' and status in {_RECEIVED}
        and captured_at >= :a and captured_at < :b
    ), refunded as (
      select coalesce(sum({_PAISE.format(col='r.amount')}) filter (where p.collection_method = 'CASH'), 0)::bigint as cash,
             coalesce(sum({_PAISE.format(col='r.amount')}) filter (where p.collection_method is distinct from 'CASH'), 0)::bigint as non_cash
      from payment_refunds r join booking_payments p on p.id = r.payment_id
      where p.salon_id = :salon and p.channel = 'manual' and r.status = 'processed'
        and r.processed_at >= :a and r.processed_at < :b
    ), spent as (
      select coalesce(sum(case entry_type when 'expense' then amount_paise else -amount_paise end)
                      filter (where payment_method = 'cash'), 0)::bigint as cash,
             coalesce(sum(case entry_type when 'expense' then amount_paise else -amount_paise end)
                      filter (where payment_method = 'non_cash'), 0)::bigint as non_cash
      from salon_expenses where salon_id = :salon and occurred_at >= :a and occurred_at < :b
    ), moved as (
      select coalesce(sum(amount_paise) filter (where direction = 'in'), 0)::bigint as cash_in,
             coalesce(sum(amount_paise) filter (where direction = 'out'), 0)::bigint as cash_out
      from salon_cash_adjustments where salon_id = :salon and occurred_at >= :a and occurred_at < :b
    ), review as (
      select
        exists (select 1 from bookings b
                where b.salon_id = :salon and b.status = 'completed' and b.payment_status = 'paid'
                  and b.completed_at >= :a and b.completed_at < :b
                  and not exists (select 1 from booking_payments p
                                  where p.booking_id = b.id and p.status in {_RECEIVED})) as paid_without_receipt,
        exists (select 1 from payment_refunds r join booking_payments p on p.id = r.payment_id
                where p.salon_id = :salon and r.status = 'created') as refund_pending
    )
    select sales.v as sales, received.cash as cash_collected, received.upi as non_cash_received,
           refunded.cash as cash_refunds, refunded.non_cash as non_cash_refunds,
           spent.cash as cash_expenses, spent.non_cash as non_cash_expenses,
           moved.cash_in as adjustments_in, moved.cash_out as adjustments_out,
           review.paid_without_receipt, review.refund_pending
    from sales, received, refunded, spent, moved, review
    """
)


def _row(mapping: Any) -> dict[str, Any]:
    return dict(mapping)


class FinanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._billing = SubscriptionBillingRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    # ---------------------------------------------------------------- salon and plan
    async def owner_salon(self, actor_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """select id, timezone, is_active, profile_completed, approval_status
                   from salons where owner_id = :actor order by is_active desc, created_at asc limit 1"""
            ),
            {"actor": actor_id},
        )
        row = result.mappings().first()
        return _row(row) if row else None

    async def plan_access(self, salon_id: str, now: datetime) -> dict[str, Any]:
        subscription = await self._billing.latest_subscription(salon_id)
        entitlement = derive_entitlement(
            status=str(subscription["status"]) if subscription else None,
            period_start=subscription["current_period_start"] if subscription else None,
            period_end=subscription["current_period_end"] if subscription else None,
            grace_end=subscription["grace_period_end"] if subscription else None,
            now=now,
        )
        access = await self._billing.booking_access(salon_id)
        return {
            "features": (subscription or {}).get("plan_features") or {},
            "entitlement_active": entitlement.active,
            "trial": TrialState(
                started_at=access.get("trial_started_at"),
                ends_at=access.get("trial_ends_at"),
                booking_limit=access.get("trial_booking_limit"),
                bookings_counted=access.get("bookings_counted"),
                limit_reached_at=access.get("trial_limit_reached_at"),
            ),
        }

    async def lock_salon(self, salon_id: str) -> None:
        await self.session.execute(text("select id from salons where id = :s for update"), {"s": salon_id})

    # ---------------------------------------------------------------- ledger reads
    async def day_figures(self, salon_id: str, start: datetime, end: datetime) -> dict[str, Any]:
        result = await self.session.execute(_DAY_SQL, {"salon": salon_id, "a": start, "b": end})
        return _row(result.mappings().one())

    async def outstanding_due(self, salon_id: str) -> int:
        result = await self.session.execute(
            text(
                """select coalesce(sum(round(greatest(total_price - (paid_amount - refunded_amount), 0) * 100)), 0)::bigint
                   from bookings where salon_id = :s and status = 'completed' and payment_status = 'unpaid'"""
            ),
            {"s": salon_id},
        )
        return int(result.scalar_one())

    async def latest_close(self, salon_id: str, local_date: date) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """select * from salon_day_closes where salon_id = :s and local_date = :d
                   order by revision desc limit 1"""
            ),
            {"s": salon_id, "d": local_date},
        )
        row = result.mappings().first()
        return _row(row) if row else None

    async def opening_cash(self, salon_id: str, local_date: date, timezone: str) -> tuple[int, str]:
        """Previous close's counted cash plus the net cash of any unclosed days since."""

        result = await self.session.execute(
            text(
                """select local_date, actual_cash_paise from salon_day_closes
                   where salon_id = :s and local_date < :d order by local_date desc, revision desc limit 1"""
            ),
            {"s": salon_id, "d": local_date},
        )
        previous = result.mappings().first()
        if previous is None:
            return 0, "not_set"
        gap_start = local_day_bounds(previous["local_date"] + timedelta(days=1), timezone)[0]
        gap_end = local_day_bounds(local_date, timezone)[0]
        net = 0
        if gap_start < gap_end:
            gap = await self.day_figures(salon_id, gap_start, gap_end)
            net = (
                gap["cash_collected"] - gap["cash_refunds"] - gap["cash_expenses"]
                + gap["adjustments_in"] - gap["adjustments_out"]
            )
        return int(previous["actual_cash_paise"]) + net, "previous_close"

    async def closes_between(self, salon_id: str, first: date, last: date) -> dict[date, dict[str, Any]]:
        result = await self.session.execute(
            text(
                """select distinct on (local_date) local_date, revision, actual_cash_paise
                   from salon_day_closes where salon_id = :s and local_date between :a and :b
                   order by local_date, revision desc"""
            ),
            {"s": salon_id, "a": first, "b": last},
        )
        return {row["local_date"]: _row(row) for row in result.mappings()}

    # ---------------------------------------------------------------- idempotent writes
    async def _replay(self, table: str, salon_id: str, key: str, request_hash: str) -> dict[str, Any] | None:
        if table not in _WRITABLE:  # the name is interpolated, so it must be one of ours
            raise ValueError(f"unknown finance table {table!r}")
        result = await self.session.execute(
            text(f"select * from {table} where salon_id = :s and idempotency_key = :k"),
            {"s": salon_id, "k": key},
        )
        row = result.mappings().first()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise IdempotencyKeyReuseError("This Idempotency-Key was already used for a different request")
        return _row(row)

    async def stored_close(self, salon_id: str, key: str, request_hash: str) -> dict[str, Any] | None:
        """The close already recorded for this key, or None. A different body is refused."""

        return await self._replay("salon_day_closes", salon_id, key, request_hash)

    async def add_expense(self, values: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = await self._replay("salon_expenses", values["salon_id"], values["key"], values["hash"])
        if existing:
            return existing, True
        result = await self.session.execute(
            text(
                """insert into salon_expenses(salon_id, entry_type, reverses_id, category, amount_paise,
                     payment_method, occurred_at, note, created_by, idempotency_key, request_hash)
                   values(:salon_id, :entry_type, :reverses_id, :category, :amount_paise, :payment_method,
                          :occurred_at, :note, :created_by, :key, :hash) returning *"""
            ),
            values,
        )
        return _row(result.mappings().one()), False

    async def get_expense(self, salon_id: str, expense_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("select * from salon_expenses where id = :i and salon_id = :s"), {"i": expense_id, "s": salon_id}
        )
        row = result.mappings().first()
        return _row(row) if row else None

    async def reversal_of(self, expense_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("select * from salon_expenses where reverses_id = :i"), {"i": expense_id}
        )
        row = result.mappings().first()
        return _row(row) if row else None

    async def list_expenses(
        self, salon_id: str, start: datetime | None, end: datetime | None, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """select e.*, exists (select 1 from salon_expenses r where r.reverses_id = e.id) as reversed
                   from salon_expenses e
                   where e.salon_id = :s and (cast(:a as timestamptz) is null or e.occurred_at >= :a)
                     and (cast(:b as timestamptz) is null or e.occurred_at < :b)
                   order by e.occurred_at desc, e.created_at desc, e.id limit :l offset :o"""
            ),
            {"s": salon_id, "a": start, "b": end, "l": limit, "o": offset},
        )
        return [_row(r) for r in result.mappings()]

    async def add_adjustment(self, values: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = await self._replay("salon_cash_adjustments", values["salon_id"], values["key"], values["hash"])
        if existing:
            return existing, True
        result = await self.session.execute(
            text(
                """insert into salon_cash_adjustments(salon_id, direction, amount_paise, reason, occurred_at,
                     reverses_id, created_by, idempotency_key, request_hash)
                   values(:salon_id, :direction, :amount_paise, :reason, :occurred_at, :reverses_id,
                          :created_by, :key, :hash) returning *"""
            ),
            values,
        )
        return _row(result.mappings().one()), False

    async def add_close(self, values: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = await self._replay("salon_day_closes", values["salon_id"], values["key"], values["hash"])
        if existing:
            return existing, True
        result = await self.session.execute(
            text(
                """insert into salon_day_closes(salon_id, local_date, revision, opening_cash_paise,
                     expected_cash_paise, actual_cash_paise, difference_reason, created_by,
                     idempotency_key, request_hash)
                   values(:salon_id, :local_date, :revision, :opening_cash_paise, :expected_cash_paise,
                          :actual_cash_paise, :difference_reason, :created_by, :key, :hash) returning *"""
            ),
            values,
        )
        return _row(result.mappings().one()), False
