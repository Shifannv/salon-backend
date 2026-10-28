"""Owner salon profile, payout, setup checklist, QR code and image routes."""

import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_session,
    get_cache,
    get_current_actor,
    get_storage_gateway,
)
from app.api.v1.routes.owner_common import owner_use_cases
from app.api.v1.schemas.platform import (
    ImageUploadUrlRequest,
    ImageUploadUrlResponse,
    OwnerPayoutAccountRequest,
    OwnerPayoutAccountResponse,
    OwnerSalonCompleteProfileRequest,
    OwnerSalonResponse,
    OwnerSalonSettingsRequest,
    OwnerSalonUpdateRequest,
    OwnerSetupStatusResponse,
    PayoutHistoryEntryResponse,
    QrCodeUrlResponse,
    SalonImageCreateRequest,
    SalonImageResponse,
    SalonImageUpdateRequest,
)
from app.application.ports.cache_gateway import CacheGateway
from app.application.ports.storage_gateway import StorageGateway
from app.core.config import settings
from app.core.qr import make_qr_svg
from app.domain.entities.profile import Profile

router = APIRouter()


# ── Salon profile ─────────────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=OwnerSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Get owner salon",
)
async def get_my_salon(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> OwnerSalonResponse:
    """Return the authenticated owner's salon."""

    salon = await owner_use_cases(session).get_my_salon(actor)
    return OwnerSalonResponse(**salon)


@router.patch(
    "/me",
    response_model=OwnerSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Update owner salon",
)
async def update_my_salon(
    payload: OwnerSalonUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> OwnerSalonResponse:
    """Update owner-editable salon profile fields."""

    salon = await owner_use_cases(session).update_my_salon(actor, payload.model_dump(exclude_unset=True))
    if "id" in salon:
        await cache.delete(f"salon:{salon['id']}:detail")
    return OwnerSalonResponse(**salon)


@router.post(
    "/me/complete-profile",
    response_model=OwnerSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete owner salon profile",
)
async def complete_profile(
    payload: OwnerSalonCompleteProfileRequest | None = None,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> OwnerSalonResponse:
    """Create/update the owner salon from onboarding data and mark it complete."""

    values = payload.model_dump(exclude_unset=True) if payload is not None else {}
    salon = await owner_use_cases(session).complete_profile(actor, values)
    return OwnerSalonResponse(**salon)


@router.patch(
    "/me/settings",
    response_model=OwnerSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Update owner salon settings",
)
async def update_settings(
    payload: OwnerSalonSettingsRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> OwnerSalonResponse:
    """Update owner salon settings (approval mode, working hours, accepting bookings)."""

    values = payload.model_dump(exclude_unset=True)
    salon = await owner_use_cases(session).update_settings(actor, values)
    if "accepting_bookings" in values:
        # Public salon payloads and the cached QR page embed accepting_bookings.
        await cache.delete_prefix(f"salon:{salon['id']}:")
        await cache.delete(f"walkin:qr:{salon['qr_token']}")
    return OwnerSalonResponse(**salon)


# ── Payout account & setup checklist ──────────────────────────────────────────


@router.get(
    "/me/payout-account",
    response_model=OwnerPayoutAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get owner payout account (masked)",
    description=(
        "Owner only. Works while the salon is still pending approval. The full bank "
        "account number is never returned, only its last 4 digits."
    ),
)
async def get_payout_account(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> OwnerPayoutAccountResponse:
    """Return the masked payout account."""

    return OwnerPayoutAccountResponse(**await owner_use_cases(session).get_payout_account(actor))


@router.put(
    "/me/payout-account",
    response_model=OwnerPayoutAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Save owner payout account",
    description=(
        "Owner only. Merge semantics: omitted fields keep their stored value, an "
        "explicit null clears a field. The merged result needs an account holder name "
        "and either a UPI ID or both account number and IFSC, otherwise 422."
    ),
)
async def put_payout_account(
    payload: OwnerPayoutAccountRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> OwnerPayoutAccountResponse:
    """Create or update the payout account and return the masked result."""

    row = await owner_use_cases(session).update_payout_account(
        actor, payload.model_dump(exclude_unset=True)
    )
    return OwnerPayoutAccountResponse(**row)


@router.get(
    "/me/payout-account/history",
    response_model=list[PayoutHistoryEntryResponse],
    status_code=status.HTTP_200_OK,
    summary="Payout account change history",
    description=(
        "Owner only. Newest first. Records who changed the destination and which fields "
        "changed; account numbers appear as their last 4 digits only."
    ),
)
async def get_payout_account_history(
    limit: int = Query(default=50, ge=1, le=200),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[PayoutHistoryEntryResponse]:
    """Return the audit trail of payout destination changes."""

    rows = await owner_use_cases(session).get_payout_history(actor, limit)
    return [
        PayoutHistoryEntryResponse(
            id=str(row["id"]),
            changed_at=row["changed_at"],
            action=row["action"],
            changed_fields=list(row["changed_fields"] or []),
            changed_by_name=row.get("changed_by_name"),
            before=row.get("before_state"),
            after=row["after_state"],
        )
        for row in rows
    ]


@router.get(
    "/me/setup-status",
    response_model=OwnerSetupStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get owner setup checklist",
)
async def get_setup_status(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> OwnerSetupStatusResponse:
    """Return which onboarding steps the owner has finished."""

    return OwnerSetupStatusResponse(**await owner_use_cases(session).get_setup_status(actor))


# ── QR code ───────────────────────────────────────────────────────────────


@router.get(
    "/me/qr",
    response_model=QrCodeUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get salon walk-in QR code URL or SVG",
    description=(
        "Returns the authenticated owner's salon QR. The QR identity comes from the "
        "salon's existing database `qr_token`; this endpoint never creates or rotates "
        "the token. Repeated requests by the same owner therefore return the same QR "
        "identity."
    ),
    responses={200: {"content": {"image/svg+xml": {}}}},
)
async def get_my_qr(
    request: Request,
    fmt: str = Query(default="url", alias="format", pattern="^(png|svg|url)$"),
    scale: int = Query(default=12, ge=4, le=30),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    """Render the authenticated owner's persisted salon QR identity."""
    salon = await owner_use_cases(session).get_business_salon(actor)
    qr_token = str(salon["qr_token"])
    if fmt == "svg":
        return Response(
            make_qr_svg(qr_token, settings.walkin_base_url, scale=scale),
            media_type="image/svg+xml",
            headers={"Content-Disposition": 'attachment; filename="salon_qr.svg"'},
        )
    if settings.public_api_base_url:
        base = str(settings.public_api_base_url).rstrip("/")
        url = f"{base}/v1/walkin/{qr_token}/qr"
    else:
        url = str(request.url_for("get_qr_image", qr_token=qr_token))
    # A stable image URL can retain obsolete QR bytes in native image caches.
    # Change its cache identity when the encoded destination changes, keeping the
    # salon's permanent QR token and normal repeated-image caching intact.
    version = hashlib.sha256(settings.walkin_base_url.rstrip("/").encode()).hexdigest()[:16]
    return JSONResponse({"url": f"{url}?format=png&scale={scale}&v={version}", "cached": False})


# ── Images ────────────────────────────────────────────────────────────────────


@router.post(
    "/me/images/upload-url",
    response_model=ImageUploadUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a signed upload URL for a salon image",
    description=(
        "Returns a short-lived signed PUT URL and the resulting public URL for "
        "uploading a salon image through the backend image validation gateway.\n\n"
        "**Upload flow:**\n"
        "1. Call this endpoint to get `upload_url` and `public_url`.\n"
        "2. `PUT <upload_url>` with the image binary and `Content-Type: <your_mime_type>` header.\n"
        "3. Call `POST /v1/salons/me/images` with `{ \"url\": \"<public_url>\" }` to record it in the DB."
    ),
)
async def get_image_upload_url(
    payload: ImageUploadUrlRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage_gateway: StorageGateway = Depends(get_storage_gateway),
) -> ImageUploadUrlResponse:
    """Generate a signed PUT URL for a direct client image upload."""

    result = await owner_use_cases(session, storage_gateway).get_image_upload_url(
        actor,
        content_type=payload.content_type,
        filename=payload.filename,
        bucket=settings.media_bucket,
    )
    return ImageUploadUrlResponse(**result)


@router.get(
    "/me/images",
    response_model=list[SalonImageResponse],
    status_code=status.HTTP_200_OK,
    summary="List owner salon images",
)
async def list_images(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[SalonImageResponse]:
    """List owner salon images."""

    rows = await owner_use_cases(session).list_images(actor)
    return [SalonImageResponse(**row) for row in rows]


@router.post(
    "/me/images",
    response_model=SalonImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create owner salon image",
)
async def create_image(
    payload: SalonImageCreateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonImageResponse:
    """Create owner salon image."""

    row = await owner_use_cases(session).create_image(actor, payload.model_dump())
    return SalonImageResponse(**row)


@router.patch(
    "/me/images/{image_id}",
    response_model=SalonImageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update owner salon image",
)
async def update_image(
    image_id: UUID,
    payload: SalonImageUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonImageResponse:
    """Update owner salon image."""

    row = await owner_use_cases(session).update_image(actor, str(image_id), payload.model_dump(exclude_unset=True))
    return SalonImageResponse(**row)


@router.delete(
    "/me/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete owner salon image",
    description=(
        "Soft-deletes the salon image (sets `is_active = false`) and best-effort "
        "removes the corresponding object from storage when the provider supports it. "
        "Returns 204 on success, 404 if the image is not found or already deleted."
    ),
)
async def delete_image(
    image_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage_gateway: StorageGateway = Depends(get_storage_gateway),
) -> Response:
    """Soft-delete a salon image and best-effort remove its stored object."""

    await owner_use_cases(session, storage_gateway).delete_image(
        actor,
        image_id=str(image_id),
        bucket=settings.media_bucket,
        r2_public_base=settings.r2_public_url or "",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
