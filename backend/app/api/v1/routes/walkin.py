"""Walk-in QR API routes — public (unauthenticated) and customer-authenticated."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, get_session
from app.api.v1.schemas.platform import (
    BookingCreateRequest,
    BookingResponse,
)
from app.api.v1.schemas.walkin import (
    WalkInSalonResponse,
    WalkInVerifyPhoneRequest,
    WalkInVerifyPhoneResponse,
)
from app.application.use_cases.walkin import WalkInUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.supabase.auth_gateway import SupabaseAuthGateway

router = APIRouter()


def _use_cases(session: AsyncSession) -> WalkInUseCases:
    return WalkInUseCases(PlatformRepository(session))


@router.get(
    "/{qr_token}",
    response_model=WalkInSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve QR token — public",
    description="Returns salon info, services, and staff for the scanned QR code. "
                "No authentication required. Rate-limited by IP.",
)
async def resolve_qr(
    qr_token: str,
    session: AsyncSession = Depends(get_session),  # no actor context needed
) -> WalkInSalonResponse:
    """Return the salon page for an unauthenticated QR scan."""

    salon = await _use_cases(session).resolve_qr_token(qr_token)
    return WalkInSalonResponse(**salon)


@router.post(
    "/{qr_token}/verify-phone",
    response_model=WalkInVerifyPhoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Send or verify phone OTP",
    description="Step 1: POST with phone only → Supabase sends OTP. "
                "Step 2: POST with phone + otp → returns JWT on success.",
)
async def verify_phone(
    qr_token: str,
    payload: WalkInVerifyPhoneRequest,
) -> WalkInVerifyPhoneResponse:
    """Send or verify a phone OTP via Supabase Auth."""

    gateway = SupabaseAuthGateway(settings)
    if payload.otp:
        result = await gateway.verify_phone_otp(payload.phone, payload.otp)
        return WalkInVerifyPhoneResponse(
            verified=True,
            access_token=result.access_token,
            refresh_token=result.refresh_token,
        )
    await gateway.send_phone_otp(payload.phone)
    return WalkInVerifyPhoneResponse(verified=False)


@router.post(
    "/{qr_token}/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create walk-in booking via QR",
    description="Creates a booking with source='qr_walkin'. "
                "Requires the JWT obtained from verify-phone.",
)
async def create_walkin_booking(
    qr_token: str,
    payload: BookingCreateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BookingResponse:
    """Create a qr_walkin booking for the authenticated customer."""

    row = await _use_cases(session).create_walkin_booking(
        actor, qr_token, payload.model_dump()
    )
    return BookingResponse(**row)
