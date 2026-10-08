"""Walk-in QR API routes — public (unauthenticated) and customer-authenticated."""

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_cache, get_current_actor, get_session
from app.api.v1.schemas.platform import (
    BookingCreateRequest,
    BookingResponse,
)
from app.api.v1.schemas.walkin import (
    WalkInSalonResponse,
    WalkInVerifyPhoneRequest,
    WalkInVerifyPhoneResponse,
)
from app.application.ports.cache_gateway import CacheGateway
from app.application.use_cases.platform import BookingUseCases
from app.application.use_cases.walkin import WalkInUseCases
from app.core.config import settings
from app.core.exceptions import TooManyRequestsError
from app.core.qr import make_qr_png, make_qr_svg
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
    cache: CacheGateway = Depends(get_cache),
) -> WalkInSalonResponse:
    """Return the salon page for an unauthenticated QR scan."""

    cache_key = f"walkin:qr:{qr_token}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return WalkInSalonResponse(**cached)

    salon = await _use_cases(session).resolve_qr_token(qr_token)
    await cache.set(cache_key, salon, ttl=180)
    return WalkInSalonResponse(**salon)


@router.get(
    "/{qr_token}/qr",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Get salon walk-in QR code image — public",
    description=(
        "Returns the QR code for this salon as a PNG (default) or SVG. "
        "No authentication required. "
        "The QR encodes: <WALKIN_BASE_URL>/<qr_token>. "
        "Embed directly in the web app or download for printing."
    ),
    responses={
        200: {
            "content": {
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/svg+xml": {"schema": {"type": "string"}},
            },
            "description": "QR code image",
        }
    },
)
async def get_qr_image(
    qr_token: str,
    fmt: str = Query(
        default="png",
        alias="format",
        pattern="^(png|svg)$",
        description="Image format: 'png' (default) or 'svg'.",
    ),
    scale: int = Query(
        default=10,
        ge=4,
        le=30,
        description="Module size. 10 ≈ 370 px wide PNG; use 20+ for print.",
    ),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Return the salon QR code image for a validated walk-in token."""

    # Validate token exists + salon is active before generating anything
    await _use_cases(session).resolve_qr_token(qr_token)
    salon_name: str = "salon"

    if fmt == "svg":
        svg_content = make_qr_svg(qr_token, settings.walkin_base_url, scale=scale)
        return StreamingResponse(
            iter([svg_content]),
            media_type="image/svg+xml",
            headers={"Content-Disposition": f'inline; filename="{salon_name}_qr.svg"'},
        )

    png_bytes = make_qr_png(qr_token, settings.walkin_base_url, scale=scale)
    return StreamingResponse(
        iter([png_bytes]),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{salon_name}_qr.png"'},
    )


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
    cache: CacheGateway = Depends(get_cache),
) -> WalkInVerifyPhoneResponse:
    """Send or verify a phone OTP via Supabase Auth."""

    if not payload.otp:
        allowed, _ = await cache.check_rate_limit(f"rate:otp:{payload.phone}", limit=5, window_seconds=60)
        if not allowed:
            raise TooManyRequestsError("Too many OTP requests. Please wait a minute before trying again.")

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
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> BookingResponse:
    """Create a qr_walkin booking for the authenticated customer."""

    if idempotency_key:
        cache_key = f"idempotency:booking:{actor.id}:{idempotency_key}"
        cached = await cache.get_idempotency(cache_key)
        if cached:
            return BookingResponse(**cached)

    repository = PlatformRepository(session)
    row = await WalkInUseCases(repository).create_walkin_booking(
        actor, qr_token, payload.model_dump()
    )
    background_tasks.add_task(
        BookingUseCases(repository).notify_new_booking_owner, row
    )

    if idempotency_key:
        await cache.set_idempotency(cache_key, row)

    return BookingResponse(**row)
