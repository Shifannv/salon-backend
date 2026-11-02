"""Super-admin payment settings (mounted under /admin): commission rate and base, minimum payout, salon rates."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, require_role
from app.api.v1.schemas.payment_settings import (
    PaymentSettingsResponse,
    PaymentSettingsUpdate,
    SalonCommissionResponse,
    SalonCommissionUpdate,
)
from app.application.use_cases.payment_settings import PaymentSettingsUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.payment_settings_repository import PaymentSettingsRepository

router = APIRouter()


def _uc(session: AsyncSession) -> PaymentSettingsUseCases:
    return PaymentSettingsUseCases(
        PaymentSettingsRepository(session),
        env_rate=settings.payment_platform_fee_percent,
        env_base=settings.payment_commission_base,
        env_version=settings.payment_commission_policy_version,
    )


@router.get("/payment-settings", response_model=PaymentSettingsResponse, summary="Commission rate, base and minimum payout")
async def get_payment_settings(
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> PaymentSettingsResponse:
    return PaymentSettingsResponse(**await _uc(session).get(actor))


@router.put(
    "/payment-settings",
    response_model=PaymentSettingsResponse,
    summary="Set the commission rate, what it is taken from, and the minimum payout",
    description="Applies to new payments only. Rate and base are set together or both cleared.",
)
async def update_payment_settings(
    payload: PaymentSettingsUpdate,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> PaymentSettingsResponse:
    return PaymentSettingsResponse(
        **await _uc(session).update(
            actor,
            rate=payload.commission_rate_percent,
            base=payload.commission_base,
            min_payout_paise=payload.min_payout_paise,
        )
    )


@router.get("/salons/{salon_id}/commission-rate", response_model=SalonCommissionResponse)
async def get_salon_commission(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonCommissionResponse:
    return SalonCommissionResponse(**await _uc(session).get_salon_rate(actor, str(salon_id)))


@router.put("/salons/{salon_id}/commission-rate", response_model=SalonCommissionResponse)
async def set_salon_commission(
    salon_id: UUID,
    payload: SalonCommissionUpdate,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonCommissionResponse:
    return SalonCommissionResponse(
        **await _uc(session).set_salon_rate(
            actor, str(salon_id), rate=payload.commission_rate_percent, note=payload.note
        )
    )


@router.delete("/salons/{salon_id}/commission-rate", response_model=SalonCommissionResponse)
async def clear_salon_commission(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonCommissionResponse:
    return SalonCommissionResponse(**await _uc(session).clear_salon_rate(actor, str(salon_id)))
