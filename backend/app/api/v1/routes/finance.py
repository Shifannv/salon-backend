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
    ExpenseBatchRequest,
    ExpenseBatchResponse,
    ExpenseChangesResponse,
    ExpenseCreateRequest,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseRuleCreateRequest,
    ExpenseRuleListResponse,
    ExpenseRuleResponse,
    ExpenseSummaryResponse,
    LedgerRangeResponse,
)
from app.application.use_cases.expense_rules import ExpenseRuleUseCases
from app.application.use_cases.finance import FinanceUseCases
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.expense_rule_repository import ExpenseRuleRepository
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
        actor, title=payload.title, category=payload.category, amount_paise=payload.amount_paise,
        payment_method=payload.payment_method, occurred_at=payload.occurred_at,
        note=payload.note, idempotency_key=idempotency_key,
    )
    return ExpenseResponse(**body)


@router.post(
    "/salons/me/expenses/batch",
    response_model=ExpenseBatchResponse,
    summary="Record up to 50 expenses at once (the phone's saved entries)",
    description=(
        "Each item carries its own `client_id`, which is its idempotency key: sending the same item again "
        "replays it. A refused item never blocks the others; see each result's `status` and `code`. "
        "The whole call is 403 `entitlement_required` once the trial or plan has ended."
    ),
)
async def add_expenses_batch(
    payload: ExpenseBatchRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseBatchResponse:
    results = await _use_cases(session).add_expenses_batch(
        actor, [item.model_dump() for item in payload.items]
    )
    return ExpenseBatchResponse(results=results)


@router.get(
    "/salons/me/expenses/changes",
    response_model=ExpenseChangesResponse,
    summary="Expense entries recorded after a cursor, oldest first",
    description="Pass `next_cursor` back as `after`. An empty answer keeps the same cursor. Readable after the plan ends.",
)
async def expense_changes(
    after: int = Query(default=0, ge=0, le=2**63 - 1),
    limit: int = Query(default=200, ge=1, le=500),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseChangesResponse:
    return ExpenseChangesResponse(**await _use_cases(session).expense_changes(actor, after=after, limit=limit))


@router.get(
    "/salons/me/expenses/summary",
    response_model=ExpenseSummaryResponse,
    summary="Per-day and month expense totals for one salon-local month (YYYY-MM)",
)
async def expense_summary(
    month: str = Query(),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseSummaryResponse:
    return ExpenseSummaryResponse(**await _use_cases(session).expense_summary(actor, month))


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


def _rule_use_cases(session: AsyncSession) -> ExpenseRuleUseCases:
    return ExpenseRuleUseCases(ExpenseRuleRepository(session))


@router.get(
    "/salons/me/expense-rules",
    response_model=ExpenseRuleListResponse,
    summary="Repeating expenses (active first). Readable after the plan ends.",
)
async def list_expense_rules(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseRuleListResponse:
    return ExpenseRuleListResponse(**await _rule_use_cases(session).list_rules(actor))


@router.post(
    "/salons/me/expense-rules",
    response_model=ExpenseRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a repeating expense",
    description=(
        "Requires `Idempotency-Key`. A rule records nothing itself: the app adds each due day as an "
        "expense with the client id `rule:<id>:<date>`. A rule cannot be edited; stop it and create another."
    ),
)
async def add_expense_rule(
    payload: ExpenseRuleCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseRuleResponse:
    body = await _rule_use_cases(session).add_rule(
        actor, title=payload.title, category=payload.category, amount_paise=payload.amount_paise,
        payment_method=payload.payment_method, note=payload.note, frequency=payload.frequency,
        start_date=payload.start_date, idempotency_key=idempotency_key,
    )
    return ExpenseRuleResponse(**body)


@router.post(
    "/salons/me/expense-rules/{rule_id}/stop",
    response_model=ExpenseRuleResponse,
    summary="Stop a repeating expense (expenses it already added stay)",
)
async def stop_expense_rule(
    rule_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ExpenseRuleResponse:
    return ExpenseRuleResponse(**await _rule_use_cases(session).stop_rule(actor, str(rule_id)))

