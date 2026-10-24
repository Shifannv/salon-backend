"""Walk-in QR API routes — public (unauthenticated) and customer-authenticated."""

import hashlib

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Path, Query, status
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
from app.core.exceptions import QrCodeNotFoundError, TooManyRequestsError
from app.core.qr import is_valid_qr_token_format, make_qr_png, make_qr_svg
from app.domain.entities.profile import Profile
from app.domain.services.checkout import online_checkout_available
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.payments.resolver import get_payment_resolver
from app.infrastructure.supabase.auth_gateway import SupabaseAuthGateway


def require_qr_token_format(
    qr_token: str = Path(description="Opaque salon QR token: 32 lowercase hex characters when issued."),
) -> str:
    """Reject a malformed token before any cache or database work, with the same 404 as an unknown one."""

    if not is_valid_qr_token_format(qr_token):
        raise QrCodeNotFoundError("Salon not found or not accepting walk-ins")
    return qr_token


router = APIRouter(dependencies=[Depends(require_qr_token_format)])


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
    fresh: bool = False,
    session: AsyncSession = Depends(get_session),  # no actor context needed
    cache: CacheGateway = Depends(get_cache),
) -> WalkInSalonResponse:
    """Return the salon page for an unauthenticated QR scan."""

    cache_key = f"walkin:qr:{qr_token}"
    cached = None if fresh else await cache.get(cache_key)
    if cached is not None:
        salon_id = await _use_cases(session).assert_public_qr_token(qr_token)
        if str(cached.get("id")) == salon_id:
            return WalkInSalonResponse(**cached)
        await cache.delete(cache_key)

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
    session: AsyncSession = Depends(get_session),
    cache: CacheGateway = Depends(get_cache),
) -> WalkInVerifyPhoneResponse:
    """Send or verify a phone OTP via Supabase Auth."""

    await _use_cases(session).assert_public_qr_token(qr_token)
    purpose = 'verify' if payload.otp else 'send'
    phone_key = hashlib.sha256(payload.phone.encode()).hexdigest()
    allowed, _ = await cache.check_rate_limit(
        f"rate:otp:{purpose}:{phone_key}", limit=10 if payload.otp else 5,
        window_seconds=60, strict=True,
    )
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

    await _use_cases(session).validate_booking_context(actor, qr_token, payload.model_dump())
    repository = PlatformRepository(session)
    row = await WalkInUseCases(
        repository, online_payments_enabled=online_checkout_available(
            get_payment_resolver().enabled, settings.booking_checkout_policy_version,
        )
    ).create_walkin_booking(
        actor, qr_token, {**payload.model_dump(), "_idempotency_key": idempotency_key}
    )
    if not row.pop("_idempotency_replay", False):
        background_tasks.add_task(
            BookingUseCases(repository).notify_new_booking_owner, row
        )

    return BookingResponse(**row)
