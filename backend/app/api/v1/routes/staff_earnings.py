"""Owner staff-earnings routes: commission rules, who did a service, earnings totals.

Owner only; staff get 403. Commission settings and earnings are never shown to staff (decision F02).
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.staff_earnings import (
    CommissionRuleCreateRequest,
    CommissionRuleListResponse,
    CommissionRuleResponse,
    ServiceStaffRequest,
    ServiceStaffResponse,
    StaffEarningsResponse,
)
from app.application.use_cases.staff_earnings import StaffEarningsUseCases
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.staff_earnings_admin_repository import (
    StaffEarningsAdminRepository,
)

router = APIRouter()


def _use_cases(session: AsyncSession) -> StaffEarningsUseCases:
    return StaffEarningsUseCases(StaffEarningsAdminRepository(session))


@router.get(
    "/salons/me/commission-rules",
    response_model=CommissionRuleListResponse,
    summary="The commission rule in force for each scope (readable after the plan ends)",
)
async def list_commission_rules(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> CommissionRuleListResponse:
    return CommissionRuleListResponse(**await _use_cases(session).list_rules(actor))


@router.post(
    "/salons/me/commission-rules",
    response_model=CommissionRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set a commission rule (a new version; earlier ones are kept)",
    description=(
        "Requires `Idempotency-Key`. Leave `staff_id` / `service_id` empty for 'any'. The most specific "
        "rule wins: staff and service, then staff, then service, then the salon default. Services "
        "completed earlier keep what they earned. A fixed amount never pays more than the service price."
    ),
)
async def add_commission_rule(
    payload: CommissionRuleCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> CommissionRuleResponse:
    body = await _use_cases(session).add_rule(
        actor,
        staff_id=str(payload.staff_id) if payload.staff_id else None,
        service_id=str(payload.service_id) if payload.service_id else None,
        commission_type=payload.commission_type, rate_basis_points=payload.rate_basis_points,
        fixed_amount_paise=payload.fixed_amount_paise, effective_from=payload.effective_from,
        idempotency_key=idempotency_key,
    )
    return CommissionRuleResponse(**body)


@router.post(
    "/salons/me/bookings/{booking_id}/services/{service_id}/staff",
    response_model=ServiceStaffResponse,
    summary="Name who does a service (only until the booking is finished)",
)
async def set_service_staff(
    booking_id: UUID,
    service_id: UUID,
    payload: ServiceStaffRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ServiceStaffResponse:
    body = await _use_cases(session).set_service_staff(
        actor, booking_id=str(booking_id), service_id=str(service_id), staff_id=str(payload.staff_id)
    )
    return ServiceStaffResponse(**body)


@router.get(
    "/salons/me/staff-earnings",
    response_model=StaffEarningsResponse,
    summary="What each staff member's completed services earned them (salon-local dates)",
)
async def staff_earnings(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> StaffEarningsResponse:
    return StaffEarningsResponse(**await _use_cases(session).earnings(actor, from_date=from_date, to_date=to_date))
