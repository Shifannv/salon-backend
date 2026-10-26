"""Read statements and record manually approved finance actions; no transfer API."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, require_role
from app.api.v1.schemas.booking_finance import (
    AdminFinanceStatement,
    FinanceCommandRequest,
    OwnerPayoutStatement,
)
from app.application.use_cases.booking_finance import BookingFinanceUseCases
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.booking_finance import BookingFinanceRepository

router = APIRouter()


@router.get('/admin/bookings/{booking_id}/finance',response_model=AdminFinanceStatement,status_code=200)
async def admin_statement(booking_id: UUID, actor: Profile = Depends(require_role(Role.super_admin)),
                          session: AsyncSession = Depends(get_authenticated_session)) -> AdminFinanceStatement:
    row = await BookingFinanceUseCases(BookingFinanceRepository(session)).statement(actor,str(booking_id),admin=True)
    return AdminFinanceStatement(**row)


@router.post('/admin/bookings/{booking_id}/finance/commands',response_model=AdminFinanceStatement,status_code=200)
async def finance_command(booking_id: UUID,payload: FinanceCommandRequest,
                          actor: Profile = Depends(require_role(Role.super_admin)),
                          session: AsyncSession = Depends(get_authenticated_session),
                          key: str | None = Header(default=None,alias='Idempotency-Key')) -> AdminFinanceStatement:
    row = await BookingFinanceUseCases(BookingFinanceRepository(session)).command(actor,str(booking_id),
        payload.expected_version,key,payload.action,payload.amount,payload.reference)
    return AdminFinanceStatement(**row)


@router.get('/salons/me/bookings/{booking_id}/payout',response_model=OwnerPayoutStatement,status_code=200)
async def owner_statement(booking_id: UUID,actor: Profile = Depends(require_role(Role.owner)),
                          session: AsyncSession = Depends(get_authenticated_session)) -> OwnerPayoutStatement:
    row = await BookingFinanceUseCases(BookingFinanceRepository(session)).statement(actor,str(booking_id))
    return OwnerPayoutStatement(**row)
