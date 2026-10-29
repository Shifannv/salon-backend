"""Owner finance cash book routes: daily ledger, expenses, cash adjustments, day close.

Owner only; the plan must include ``daily_ledger`` (a salon on its free trial counts). Money is
integer paise. Writes need an ``Idempotency-Key``. This is an operational cash book, not tax
accounting and not a profit figure.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.finance import (
    AdjustmentCreateRequest,
    AdjustmentResponse,
    DailyLedgerResponse,
    DayCloseRequest,
    ExpenseCreateRequest,
    ExpenseListResponse,
    ExpenseResponse,
    LedgerRangeResponse,
)
from app.application.use_cases.finance import FinanceUseCases
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.finance_repository import FinanceRepository

router = APIRouter()


def _use_cases(session: AsyncSession) -> FinanceUseCases:
    return FinanceUseCases(FinanceRepository(session))


@router.get(
    "/salons/me/ledger/daily",
    response_model=DailyLedgerResponse,
    summary="One salon-local day of the cash book",
    description="An empty day returns zero totals. `needs_review` means do not show the totals as final.",
)
async def daily_ledger(
    date: date,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> DailyLedgerResponse:
    return DailyLedgerResponse(**await _use_cases(session).daily_ledger(actor, date))


@router.get(
    "/salons/me/ledger/range",
    response_model=LedgerRangeResponse,
    summary="Per-day cash book totals for a date range (at most 93 days)",
)
async def ledger_range(
    from_: date = Query(alias="from"),
    to: date = Query(),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> LedgerRangeResponse:
    return LedgerRangeResponse(**await _use_cases(session).ledger_range(actor, from_, to))


@router.post(
    "/salons/me/ledger/days/{local_date}/close",
    response_model=DailyLedgerResponse,
    summary="Record the counted cash for a day",
    description=(
        "Requires `Idempotency-Key`. The server computes the expected cash; a difference needs "
        "`difference_reason`. A later correction is a cash adjustment or a new close revision."
    ),
)
async def close_day(
    local_date: date,
    payload: DayCloseRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> DailyLedgerResponse:
    body = await _use_cases(session).close_day(
        actor, local_date, actual_cash_paise=payload.actual_cash_paise,
        difference_reason=payload.difference_reason, opening_cash_paise=payload.opening_cash_paise,
        idempotency_key=idempotency_key,
    )
    return DailyLedgerResponse(**body)


@router.post(
    "/salons/me/ledger/adjustments",
    response_model=AdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an audited cash adjustment (cash in or out, with a reason)",
)
async def add_adjustment(
    payload: AdjustmentCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AdjustmentResponse:
    body = await _use_cases(session).add_adjustment(
        actor, direction=payload.direction, amount_paise=payload.amount_paise,
        reason=payload.reason, occurred_at=payload.occurred_at, idempotency_key=idempotency_key,
    )
    return AdjustmentResponse(**body)


@router.post(
    "/salons/me/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an expense",
    description="Requires `Idempotency-Key`. Not a tax invoice or official accounting ledger.",
)
async def add_expense(
    payload: ExpenseCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseResponse:
    body = await _use_cases(session).add_expense(
        actor, category=payload.category, amount_paise=payload.amount_paise,
        payment_method=payload.payment_method, occurred_at=payload.occurred_at,
        note=payload.note, idempotency_key=idempotency_key,
    )
    return ExpenseResponse(**body)


@router.get(
    "/salons/me/expenses",
    response_model=ExpenseListResponse,
    summary="List expenses and their reversals, newest first",
)
async def list_expenses(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseListResponse:
    body = await _use_cases(session).list_expenses(
        actor, first=from_, last=to, limit=limit, offset=offset
    )
    return ExpenseListResponse(**body)


@router.post(
    "/salons/me/expenses/{expense_id}/reverse",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reverse an expense (appends a mirror entry; the original is never edited)",
)
async def reverse_expense(
    expense_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseResponse:
    body = await _use_cases(session).reverse_expense(
        actor, str(expense_id), idempotency_key=idempotency_key
    )
    return ExpenseResponse(**body)
