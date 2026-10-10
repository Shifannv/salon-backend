"""Barber/owner app API routes."""

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_session,
    get_cache,
    get_current_actor,
    get_storage_gateway,
)
from app.api.v1.schemas.platform import (
    BlockedSlotCreateRequest,
    BlockedSlotResponse,
    HolidayCreateRequest,
    HolidayResponse,
    ImageUploadUrlRequest,
    ImageUploadUrlResponse,
    LanguageResponse,
    OwnerSalonCompleteProfileRequest,
    OwnerSalonResponse,
    OwnerSalonSettingsRequest,
    OwnerSalonUpdateRequest,
    SalonImageCreateRequest,
    SalonImageResponse,
    SalonImageUpdateRequest,
    ServiceCreateRequest,
    ServiceResponse,
    ServiceUpdateRequest,
    StaffCreateRequest,
    StaffResponse,
    StaffServiceAssignRequest,
    StaffServiceLanguagesRequest,
    StaffServiceResponse,
    StaffUpdateRequest,
)
from app.application.ports.cache_gateway import CacheGateway
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.platform import OwnerUseCases
from app.core.config import settings
from app.core.qr import make_qr_svg
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


def _use_cases(
    session: AsyncSession,
    storage_gateway: StorageGateway | None = None,
) -> OwnerUseCases:
    return OwnerUseCases(
        PlatformRepository(session), storage_gateway=storage_gateway or get_storage_gateway(),
        service_media_base=settings.r2_public_url,
    )


def _bucket() -> str:
    """Return the configured R2 bucket name, falling back to the default."""
    return settings.r2_bucket or "salon-images"


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

    salon = await _use_cases(session).get_my_salon(actor)
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

    salon = await _use_cases(session).update_my_salon(actor, payload.model_dump(exclude_unset=True))
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
    salon = await _use_cases(session).complete_profile(actor, values)
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
) -> OwnerSalonResponse:
    """Update owner salon settings (approval mode and working hours)."""

    salon = await _use_cases(session).update_my_salon(actor, payload.model_dump(exclude_unset=True))
    return OwnerSalonResponse(**salon)


# ── QR code ───────────────────────────────────────────────────────────────


class QrCodeUrlResponse(BaseModel):
    """Public image URL that can be displayed without an Authorization header."""

    url: str
    cached: bool = False


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
    salon = await _use_cases(session).get_business_salon(actor)
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
    return JSONResponse({"url": f"{url}?format=png&scale={scale}", "cached": False})


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

    result = await _use_cases(session, storage_gateway).get_image_upload_url(
        actor,
        content_type=payload.content_type,
        filename=payload.filename,
        bucket=_bucket(),
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

    rows = await _use_cases(session).list_images(actor)
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

    row = await _use_cases(session).create_image(actor, payload.model_dump())
    return SalonImageResponse(**row)


@router.patch(
    "/me/images/{image_id}",
    response_model=SalonImageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update owner salon image",
)
async def update_image(
    image_id: str,
    payload: SalonImageUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonImageResponse:
    """Update owner salon image."""

    row = await _use_cases(session).update_image(actor, image_id, payload.model_dump(exclude_unset=True))
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
    image_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage_gateway: StorageGateway = Depends(get_storage_gateway),
) -> Response:
    """Soft-delete a salon image and best-effort remove its stored object."""

    await _use_cases(session, storage_gateway).delete_image(
        actor,
        image_id=image_id,
        bucket=_bucket(),
        r2_public_base=settings.r2_public_url or "",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Holidays ──────────────────────────────────────────────────────────────────


@router.get(
    "/me/holidays",
    response_model=list[HolidayResponse],
    status_code=status.HTTP_200_OK,
    summary="List owner salon holidays",
)
async def list_holidays(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[HolidayResponse]:
    """List owner salon holidays."""

    rows = await _use_cases(session).list_holidays(actor)
    return [HolidayResponse(**row) for row in rows]


@router.post(
    "/me/holidays",
    response_model=HolidayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create owner salon holiday",
)
async def create_holiday(
    payload: HolidayCreateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> HolidayResponse:
    """Create owner salon holiday."""

    row = await _use_cases(session).create_holiday(actor, payload.model_dump())
    return HolidayResponse(**row)


@router.delete(
    "/me/holidays/{holiday_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete owner salon holiday",
)
async def delete_holiday(
    holiday_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    """Soft-delete a holiday owned by the authenticated owner's salon."""

    await _use_cases(session).delete_holiday(actor, holiday_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Services ──────────────────────────────────────────────────────────────────


@router.get("/me/services", response_model=list[ServiceResponse], status_code=status.HTTP_200_OK)
async def list_services(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[ServiceResponse]:
    """List owner salon services."""

    rows = await _use_cases(session).list_services(actor)
    return [ServiceResponse(**row) for row in rows]


@router.post(
    "/me/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create owner salon service",
)
async def create_service(
    payload: ServiceCreateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> ServiceResponse:
    """Create owner salon service."""

    row = await _use_cases(session).create_service(actor, payload.model_dump())
    if "salon_id" in row:
        await cache.delete(f"salon:{row['salon_id']}:services")
        await cache.delete(f"salon:{row['salon_id']}:detail")
        await cache.delete_prefix("walkin:qr:")
    return ServiceResponse(**row)


@router.patch(
    "/me/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update owner salon service",
)
async def update_service(
    service_id: str,
    payload: ServiceUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> ServiceResponse:
    """Update owner salon service."""

    row = await _use_cases(session).update_service(actor, service_id, payload.model_dump(exclude_unset=True))
    if "salon_id" in row:
        await cache.delete(f"salon:{row['salon_id']}:services")
        await cache.delete(f"salon:{row['salon_id']}:detail")
        await cache.delete_prefix("walkin:qr:")
    return ServiceResponse(**row)


@router.delete(
    "/me/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate owner salon service",
)
async def deactivate_service(
    service_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> ServiceResponse:
    """Soft-delete owner salon service."""

    row = await _use_cases(session).deactivate_service(actor, service_id)
    if "salon_id" in row:
        await cache.delete(f"salon:{row['salon_id']}:services")
        await cache.delete(f"salon:{row['salon_id']}:detail")
        await cache.delete_prefix("walkin:qr:")
    return ServiceResponse(**row)


# ── Staff ─────────────────────────────────────────────────────────────────────


@router.get("/me/staff", response_model=list[StaffResponse], status_code=status.HTTP_200_OK)
async def list_staff(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[StaffResponse]:
    """List owner salon staff."""

    rows = await _use_cases(session).list_staff(actor)
    return [StaffResponse(**row) for row in rows]


@router.post(
    "/me/staff",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create owner salon staff",
)
async def create_staff(
    payload: StaffCreateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> StaffResponse:
    """Create owner salon staff."""

    row = await _use_cases(session).create_staff(actor, payload.model_dump())
    if "salon_id" in row:
        await cache.delete(f"salon:{row['salon_id']}:staff")
    return StaffResponse(**row)


@router.patch(
    "/me/staff/{staff_id}",
    response_model=StaffResponse,
    status_code=status.HTTP_200_OK,
    summary="Update owner salon staff",
)
async def update_staff(
    staff_id: str,
    payload: StaffUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> StaffResponse:
    """Update owner salon staff."""

    row = await _use_cases(session).update_staff(actor, staff_id, payload.model_dump(exclude_unset=True))
    if "salon_id" in row:
        await cache.delete(f"salon:{row['salon_id']}:staff")
    return StaffResponse(**row)


@router.delete(
    "/me/staff/{staff_id}",
    response_model=StaffResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate owner salon staff",
)
async def deactivate_staff(
    staff_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> StaffResponse:
    """Soft-delete owner salon staff."""

    row = await _use_cases(session).deactivate_staff(actor, staff_id)
    if "salon_id" in row:
        await cache.delete(f"salon:{row['salon_id']}:staff")
    return StaffResponse(**row)


@router.post(
    "/me/staff/{staff_id}/services",
    response_model=StaffServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign service to staff",
)
async def assign_staff_service(
    staff_id: str,
    payload: StaffServiceAssignRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> StaffServiceResponse:
    """Assign a salon service to staff (with optional duration/price overrides)."""

    row = await _use_cases(session).assign_staff_service(actor, staff_id, payload.model_dump())
    return StaffServiceResponse(**row)


@router.get(
    "/me/staff/{staff_id}/services",
    response_model=list[StaffServiceResponse],
    status_code=status.HTTP_200_OK,
    summary="List services assigned to staff",
)
async def list_staff_services(
    staff_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[StaffServiceResponse]:
    """Return service assignments for a staff member."""

    rows = await _use_cases(session).list_staff_services(actor, staff_id)
    return [StaffServiceResponse(**row) for row in rows]


@router.post(
    "/me/staff/{staff_id}/photo-upload-url",
    response_model=ImageUploadUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a signed upload URL for a staff photo",
    description=(
        "Returns a short-lived signed PUT URL and the resulting public URL for "
        "uploading a staff photo through the backend image validation gateway.\n\n"
        "**Upload flow:**\n"
        "1. Call this endpoint to get `upload_url` and `public_url`.\n"
        "2. `PUT <upload_url>` with the image binary and `Content-Type: <your_mime_type>` header.\n"
        "3. Call `PATCH /v1/salons/me/staff/{staff_id}` with `{ \"photo_url\": \"<public_url>\" }` to persist."
    ),
)
async def get_staff_photo_upload_url(
    staff_id: str,
    payload: ImageUploadUrlRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage_gateway: StorageGateway = Depends(get_storage_gateway),
) -> ImageUploadUrlResponse:
    """Generate a signed PUT URL for a direct staff photo upload."""

    result = await _use_cases(session, storage_gateway).get_staff_photo_upload_url(
        actor,
        staff_id=staff_id,
        content_type=payload.content_type,
        filename=payload.filename,
        bucket=_bucket(),
    )
    return ImageUploadUrlResponse(**result)


# ── Staff service languages ───────────────────────────────────────────────────


@router.get(
    "/me/staff/{staff_id}/services/{staff_service_id}/languages",
    response_model=list[LanguageResponse],
    status_code=status.HTTP_200_OK,
    summary="List languages for a staff service assignment",
)
async def list_staff_service_languages(
    staff_id: str,
    staff_service_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[LanguageResponse]:
    """Return the languages a staff member supports for a specific service."""

    rows = await _use_cases(session).list_staff_service_languages(actor, staff_id, staff_service_id)
    return [LanguageResponse(**row) for row in rows]


@router.put(
    "/me/staff/{staff_id}/services/{staff_service_id}/languages",
    response_model=list[LanguageResponse],
    status_code=status.HTTP_200_OK,
    summary="Set languages for a staff service assignment",
    description=(
        "Idempotent PUT — replaces the full language list. "
        "Send an empty list to remove all languages."
    ),
)
async def set_staff_service_languages(
    staff_id: str,
    staff_service_id: str,
    payload: StaffServiceLanguagesRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[LanguageResponse]:
    """Replace the language list for a staff service assignment."""

    rows = await _use_cases(session).set_staff_service_languages(
        actor, staff_id, staff_service_id, payload.language_codes
    )
    return [LanguageResponse(**row) for row in rows]


# ── Blocked slots ─────────────────────────────────────────────────────────────


@router.get(
    "/me/blocks",
    response_model=list[BlockedSlotResponse],
    status_code=status.HTTP_200_OK,
    summary="List blocked slots for this salon",
)
async def list_blocked_slots(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[BlockedSlotResponse]:
    """Return all blocked slots (staff-scoped and salon-wide) for the owner's salon."""

    rows = await _use_cases(session).list_blocked_slots(actor)
    return [BlockedSlotResponse(**row) for row in rows]


@router.post(
    "/me/blocks",
    response_model=BlockedSlotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a blocked slot",
    description=(
        "Create a staff-scoped block (set staff_id) or a salon-wide block (leave staff_id null). "
        "Slot engine honours both when computing availability."
    ),
)
async def create_blocked_slot(
    payload: BlockedSlotCreateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BlockedSlotResponse:
    """Create a blocked slot."""

    row = await _use_cases(session).create_blocked_slot(actor, payload.model_dump())
    return BlockedSlotResponse(**row)


@router.delete(
    "/me/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a blocked slot",
)
async def delete_blocked_slot(
    block_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    """Hard-delete a blocked slot. Blocked slots have no is_active column in the schema."""

    await _use_cases(session).delete_blocked_slot(actor, block_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
