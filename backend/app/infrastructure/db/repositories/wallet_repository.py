"""Owner wallet queries and payout-request writes (0053). Money is integer paise.

The wallet balance is never stored. What the platform holds for a salon is read from the payment
ledger: gateway payments whose money the platform collected (``platform_collect``), less the
commission snapshot, less processed refunds. Payments settled straight to the salon
(``direct_to_salon``) and manual receipts are not the platform's to pay out and are left out.
Payout requests are the only rows written here.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IdempotencyKeyReuseError, ValidationError
from app.infrastructure.db.repositories.finance_repository import FinanceRepository

_SETTLED = "('captured','partially_refunded','refunded')"
_PAISE = "round(({expr}) * 100)::bigint"

_TOTALS_SQL = text(
    f"""
    with paid_in as (
      select coalesce(sum({_PAISE.format(expr='p.amount - p.overcollected_amount')}), 0)::bigint as collected,
             coalesce(sum({_PAISE.format(expr='p.platform_commission_amount')}), 0)::bigint as commission
      from booking_payments p
      where p.salon_id = :s and p.channel = 'gateway' and p.settlement_model = 'platform_collect'
        and p.status in {_SETTLED}
    ), refunded as (
      select coalesce(sum({_PAISE.format(expr='r.amount')}), 0)::bigint as refunded,
             coalesce(sum({_PAISE.format(expr='r.commission_reversal_amount')}), 0)::bigint as reversed
      from payment_refunds r join booking_payments p on p.id = r.payment_id
      where p.salon_id = :s and p.channel = 'gateway' and p.settlement_model = 'platform_collect'
        and r.status = 'processed' and not r.applies_to_excess
    ), asked as (
      select coalesce(sum(amount_paise) filter (where status = 'requested'), 0)::bigint as requested,
             coalesce(sum(amount_paise) filter (where status = 'paid'), 0)::bigint as paid
      from salon_payout_requests where salon_id = :s
    )
    select paid_in.collected, paid_in.commission, refunded.refunded, refunded.reversed,
           asked.requested, asked.paid
    from paid_in, refunded, asked
    """
)

_FEED_SQL = text(
    f"""
    with feed as (
      select p.id::text as id, 'earning'::text as kind, 'credit'::text as direction,
             {_PAISE.format(expr='p.amount - p.overcollected_amount - p.platform_commission_amount')} as amount_paise,
             'completed'::text as status, null::text as reference, null::text as reject_reason,
             null::date as scheduled_for, false as can_cancel,
             coalesce(p.captured_at, p.created_at) as happened_at
      from booking_payments p
      where p.salon_id = :s and p.channel = 'gateway' and p.settlement_model = 'platform_collect'
        and p.status in {_SETTLED}
      union all
      select r.id::text, 'refund', 'debit',
             {_PAISE.format(expr='r.amount - r.commission_reversal_amount')},
             'completed', null, null, null, false, coalesce(r.processed_at, r.created_at)
      from payment_refunds r join booking_payments p on p.id = r.payment_id
      where p.salon_id = :s and p.channel = 'gateway' and p.settlement_model = 'platform_collect'
        and r.status = 'processed' and not r.applies_to_excess
      union all
      select q.id::text, 'payout', 'debit', q.amount_paise, q.status, q.reference, q.reject_reason,
             q.scheduled_for, q.status = 'requested', q.created_at
      from salon_payout_requests q where q.salon_id = :s
    )
    select * from feed
    where cast(:after_at as timestamptz) is null
       or (happened_at, id) < (cast(:after_at as timestamptz), cast(:after_id as text))
    order by happened_at desc, id desc
    limit :limit
    """
)

_REQUEST_COLUMNS = (
    "q.id::text as id, q.salon_id::text as salon_id, q.amount_paise, q.scheduled_for, q.status, "
    "q.reference, q.reject_reason, q.created_at, q.processed_at, q.cancelled_at, "
    "q.idempotency_key, q.request_hash"
)


def _row(mapping: Any) -> dict[str, Any]:
    return dict(mapping)


def encode_cursor(happened_at: datetime, row_id: str) -> str:
    return base64.urlsafe_b64encode(f"{happened_at.isoformat()}|{row_id}".encode()).decode()


def decode_cursor(cursor: str | None) -> tuple[datetime | None, str | None]:
    """The (time, id) the next page starts after. A malformed cursor is the caller's error."""

    if not cursor:
        return None, None
    try:
        moment, row_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|", 1)
        return datetime.fromisoformat(moment), row_id
    except (ValueError, binascii.Error, UnicodeDecodeError) as error:
        raise ValidationError("The page cursor is not valid") from error


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._finance = FinanceRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    # ---------------------------------------------------------------- salon
    async def owner_salon(self, actor_id: str) -> dict[str, Any] | None:
        return await self._finance.owner_salon(actor_id)

    async def lock_salon(self, salon_id: str) -> None:
        """Serialise wallet writers for one salon, so two requests cannot both spend one balance."""

        await self._finance.lock_salon(salon_id)

    async def payout_account_ready(self, salon_id: str) -> bool:
        """Whether bank or UPI details exist. Answered inside Postgres: the number is never read."""

        result = await self.session.execute(
            text(
                """select (coalesce(btrim(upi_id), '') <> '' or bank_account_number is not null)
                   from salon_payout_accounts where salon_id = :s"""
            ),
            {"s": salon_id},
        )
        return bool(result.scalar())

    # ---------------------------------------------------------------- reads
    async def totals(self, salon_id: str) -> dict[str, int]:
        result = await self.session.execute(_TOTALS_SQL, {"s": salon_id})
        return {key: int(value) for key, value in result.mappings().one().items()}

    async def entries(self, salon_id: str, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        after_at, after_id = decode_cursor(cursor)
        result = await self.session.execute(
            _FEED_SQL, {"s": salon_id, "after_at": after_at, "after_id": after_id, "limit": limit + 1}
        )
        rows = [_row(row) for row in result.mappings()]
        more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = encode_cursor(rows[-1]["happened_at"], rows[-1]["id"]) if more and rows else None
        return rows, next_cursor

    # ---------------------------------------------------------------- payout requests
    async def get_request(self, request_id: str, *, salon_id: str | None = None, lock: bool = False) -> dict[str, Any] | None:
        """One request, optionally limited to a salon (an owner must never reach another's)."""

        result = await self.session.execute(
            text(
                f"""select {_REQUEST_COLUMNS} from salon_payout_requests q
                    where q.id = cast(:id as uuid) and (cast(:s as uuid) is null or q.salon_id = cast(:s as uuid))
                    {'for no key update' if lock else ''}"""
            ),
            {"id": request_id, "s": salon_id},
        )
        row = result.mappings().first()
        return _row(row) if row else None

    async def stored_request(self, salon_id: str, key: str, request_hash: str) -> dict[str, Any] | None:
        """The request already recorded for this key, or None. A different body is refused."""

        result = await self.session.execute(
            text(
                f"""select {_REQUEST_COLUMNS} from salon_payout_requests q
                    where q.salon_id = cast(:s as uuid) and q.idempotency_key = :k"""
            ),
            {"s": salon_id, "k": key},
        )
        existing = result.mappings().first()
        if existing is None:
            return None
        if existing["request_hash"] != request_hash:
            raise IdempotencyKeyReuseError("This Idempotency-Key was already used for a different request")
        return _row(existing)

    async def add_request(self, values: dict[str, Any]) -> dict[str, Any]:
        """Insert one new request. Callers hold the salon lock and have checked ``stored_request``."""

        created = await self.session.execute(
            text(
                """insert into salon_payout_requests
                     (salon_id, amount_paise, scheduled_for, requested_by, idempotency_key, request_hash)
                   values (cast(:salon_id as uuid), :amount_paise, :scheduled_for,
                           cast(:requested_by as uuid), :key, :hash)
                   returning id::text as id"""
            ),
            values,
        )
        row = await self.get_request(created.scalar_one(), salon_id=values["salon_id"])
        assert row is not None  # just inserted in this transaction
        return row

    async def cancel_request(self, request_id: str) -> dict[str, Any]:
        await self.session.execute(
            text(
                """update salon_payout_requests set status = 'cancelled', cancelled_at = now()
                   where id = cast(:id as uuid) and status = 'requested'"""
            ),
            {"id": request_id},
        )
        row = await self.get_request(request_id)
        assert row is not None
        return row

    async def finish_request(
        self, request_id: str, *, status: str, admin_id: str, reference: str | None, reject_reason: str | None
    ) -> dict[str, Any]:
        """Move a waiting request to 'paid' or 'rejected'. The status guard keeps it to one move."""

        await self.session.execute(
            text(
                """update salon_payout_requests
                   set status = :status, reference = :reference, reject_reason = :reason,
                       processed_by = cast(:admin as uuid), processed_at = now()
                   where id = cast(:id as uuid) and status = 'requested'"""
            ),
            {"id": request_id, "status": status, "admin": admin_id, "reference": reference, "reason": reject_reason},
        )
        row = await self.get_request(request_id)
        assert row is not None
        return row

    async def queue(self, status: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        """Requests across all salons for the admin, soonest day first, with masked payout details."""

        after_at, after_id = decode_cursor(cursor)
        result = await self.session.execute(
            text(
                f"""select {_REQUEST_COLUMNS}, s.name as salon_name,
                           a.account_holder_name, a.upi_id, a.bank_name, a.bank_account_last4, a.ifsc
                    from salon_payout_requests q join salons s on s.id = q.salon_id
                    left join lateral salon_payout_account_masked(q.salon_id) a on true
                    where (cast(:status as text) is null or q.status = cast(:status as text))
                      and (cast(:after_at as timestamptz) is null
                           or (q.created_at, q.id::text) > (cast(:after_at as timestamptz), cast(:after_id as text)))
                    order by q.created_at asc, q.id::text asc
                    limit :limit"""
            ),
            {"status": status, "after_at": after_at, "after_id": after_id, "limit": limit + 1},
        )
        rows = [_row(row) for row in result.mappings()]
        more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = encode_cursor(rows[-1]["created_at"], rows[-1]["id"]) if more and rows else None
        return rows, next_cursor
