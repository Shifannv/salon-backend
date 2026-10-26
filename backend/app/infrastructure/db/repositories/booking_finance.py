"""Backend-only financial records with explicit redacted owner projections."""

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BookingChangeError,
    ForbiddenError,
    IdempotencyKeyReuseError,
    NotFoundError,
    ServiceUnavailableError,
)

_ERRORS = {
    "finance_version_conflict": "This statement changed. Refresh it before continuing.",
    "finance_already_approved": "Costs cannot change after payout approval. Reconciliation is required.",
    "finance_reconciliation_required": "Confirm held funds, costs and completed refunds before approval or payout recording.",
    "invalid_payout_amount": "The amount exceeds the available approved payout or is not positive.",
    "invalid_finance_command": "Check the finance action, amount and reference.",
}


class BookingFinanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _failure(self, exc: DBAPIError) -> None:
        await self.session.rollback()
        code = getattr(exc.orig, 'sqlstate', None)
        if code in {'42P01','42703','42883'}:
            raise ServiceUnavailableError("Financial records require the reviewed database migration") from exc
        if code not in {'P0001','23514','23505'}:
            raise exc
        message = str(exc.orig)
        if 'finance_admin_required' in message:
            raise ForbiddenError("Finance administrator access required") from exc
        if 'finance_not_found' in message:
            raise NotFoundError("Financial statement not found") from exc
        if 'idempotency_key_reused' in message or code == '23505':
            raise IdempotencyKeyReuseError("This command key or payout reference was already used") from exc
        for reason, public in _ERRORS.items():
            if reason in message:
                raise BookingChangeError(reason, public) from exc
        raise BookingChangeError('finance_conflict', 'This financial action could not be completed') from exc

    async def statement(self, booking_id: str, actor_id: str, *, admin: bool) -> dict[str, Any]:
        # Never load the private columns for an owner statement.
        columns = 'f.*' if admin else """f.booking_id,f.approved_amount,f.paid_out_amount,
          case when f.captured_amount=0 or f.kind='salon_cancellation' then 'not_applicable'
            when f.requires_reconciliation or f.approved_amount=0 then 'under_review'
            when f.paid_out_amount=f.approved_amount then 'paid' else 'approved' end as status"""
        predicate = "exists(select 1 from public.profiles where id=cast(:actor as uuid) and role='super_admin' and is_active)" if admin else "s.owner_id=cast(:actor as uuid)"
        try:
            result = await self.session.execute(text(f"""
                select {columns} from public.booking_financial_outcomes f
                join public.bookings b on b.id=f.booking_id join public.salons s on s.id=b.salon_id
                where f.booking_id=cast(:booking as uuid) and {predicate}
            """),{'booking':booking_id,'actor':actor_id})
            row = result.mappings().one_or_none()
            if row is None:
                raise NotFoundError("Financial statement not found")
            return dict(row)
        except DBAPIError as exc:
            await self._failure(exc)
            raise

    async def command(self, booking_id: str, version: int, key: str, action: str, amount: Decimal, reference: str) -> None:
        try:
            await self.session.execute(text("""
                select public.manage_booking_finance(cast(:booking as uuid),:version,:key,:action,:amount,:reference)
            """),{'booking':booking_id,'version':version,'key':key,'action':action,'amount':amount,'reference':reference})
            await self.session.commit()
        except DBAPIError as exc:
            await self._failure(exc)
            raise
