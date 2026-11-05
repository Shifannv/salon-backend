"""Owner service, staff and staff-service language routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_session,
    get_cache,
    get_current_actor,
    get_storage_gateway,
)
from app.api.v1.routes.owner_common import owner_use_cases
from app.api.v1.schemas.catalog import ServiceBatchCreateRequest, StaffCapabilitiesRequest
from app.api.v1.schemas.platform import (
    ImageUploadUrlRequest,
    ImageUploadUrlResponse,
    LanguageResponse,
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
from app.core.config import settings
from app.domain.entities.profile import Profile

router = APIRouter()


@router.get("/me/staff/{staff_id}/capabilities", response_model=StaffCapabilitiesRequest, status_code=200)
async def get_staff_capabilities(staff_id: UUID, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session)) -> StaffCapabilitiesRequest:
    return StaffCapabilitiesRequest(**await owner_use_cases(session).get_staff_capabilities(actor,str(staff_id)))


@router.put("/me/staff/{staff_id}/capabilities", response_model=StaffCapabilitiesRequest, status_code=200)
async def set_staff_capabilities(staff_id: UUID, payload: StaffCapabilitiesRequest, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session)) -> StaffCapabilitiesRequest:
    return StaffCapabilitiesRequest(**await owner_use_cases(session).set_staff_capabilities(actor,str(staff_id),payload.model_dump()))



@router.post("/me/services/batch", response_model=list[ServiceResponse], status_code=status.HTTP_201_CREATED)
async def create_services(payload: ServiceBatchCreateRequest, actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session), cache: CacheGateway = Depends(get_cache)) -> list[ServiceResponse]:
    rows = await owner_use_cases(session).create_services(actor, [item.model_dump() for item in payload.services])
    if rows:
        await cache.delete(f"salon:{rows[0]['salon_id']}:services")
        await cache.delete(f"salon:{rows[0]['salon_id']}:detail")
        await cache.delete_prefix("walkin:qr:")
    return [ServiceResponse(**row) for row in rows]



# ── Services ──────────────────────────────────────────────────────────────────


@router.get("/me/services", response_model=list[ServiceResponse], status_code=status.HTTP_200_OK)
async def list_services(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[ServiceResponse]:
    """List owner salon services."""

    rows = await owner_use_cases(session).list_services(actor)
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

    row = await owner_use_cases(session).create_service(actor, payload.model_dump())
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
    service_id: UUID,
    payload: ServiceUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> ServiceResponse:
    """Update owner salon service."""

    row = await owner_use_cases(session).update_service(actor, str(service_id), payload.model_dump(exclude_unset=True))
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
    service_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> ServiceResponse:
    """Soft-delete owner salon service."""

    row = await owner_use_cases(session).deactivate_service(actor, str(service_id))
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

    rows = await owner_use_cases(session).list_staff(actor)
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

    row = await owner_use_cases(session).create_staff(actor, payload.model_dump())
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
    staff_id: UUID,
    payload: StaffUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> StaffResponse:
    """Update owner salon staff."""

    row = await owner_use_cases(session).update_staff(actor, str(staff_id), payload.model_dump(exclude_unset=True))
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
    staff_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> StaffResponse:
    """Soft-delete owner salon staff."""

    row = await owner_use_cases(session).deactivate_staff(actor, str(staff_id))
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
    staff_id: UUID,
    payload: StaffServiceAssignRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> StaffServiceResponse:
    """Assign a salon service to staff (with optional duration/price overrides)."""

    row = await owner_use_cases(session).assign_staff_service(actor, str(staff_id), payload.model_dump())
    return StaffServiceResponse(**row)


@router.get(
    "/me/staff/{staff_id}/services",
    response_model=list[StaffServiceResponse],
    status_code=status.HTTP_200_OK,
    summary="List services assigned to staff",
)
async def list_staff_services(
    staff_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[StaffServiceResponse]:
    """Return service assignments for a staff member."""

    rows = await owner_use_cases(session).list_staff_services(actor, str(staff_id))
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
    staff_id: UUID,
    payload: ImageUploadUrlRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage_gateway: StorageGateway = Depends(get_storage_gateway),
) -> ImageUploadUrlResponse:
    """Generate a signed PUT URL for a direct staff photo upload."""

    result = await owner_use_cases(session, storage_gateway).get_staff_photo_upload_url(
        actor,
        staff_id=str(staff_id),
        content_type=payload.content_type,
        filename=payload.filename,
        bucket=settings.media_bucket,
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
    staff_id: UUID,
    staff_service_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[LanguageResponse]:
    """Return the languages a staff member supports for a specific service."""

    rows = await owner_use_cases(session).list_staff_service_languages(actor, str(staff_id), str(staff_service_id))
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
    staff_id: UUID,
    staff_service_id: UUID,
    payload: StaffServiceLanguagesRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[LanguageResponse]:
    """Replace the language list for a staff service assignment."""

    rows = await owner_use_cases(session).set_staff_service_languages(
        actor, str(staff_id), str(staff_service_id), payload.language_codes
    )
    return [LanguageResponse(**row) for row in rows]
