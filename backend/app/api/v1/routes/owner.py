"""Barber/owner app API routes."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.platform import (
    BlockedSlotCreateRequest,
    BlockedSlotResponse,
    HolidayCreateRequest,
    HolidayResponse,
    LanguageResponse,
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
from app.application.use_cases.platform import OwnerUseCases
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


def _use_cases(session: AsyncSession) -> OwnerUseCases:
    return OwnerUseCases(PlatformRepository(session))


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
) -> OwnerSalonResponse:
    """Update owner-editable salon profile fields."""

    salon = await _use_cases(session).update_my_salon(actor, payload.model_dump(exclude_unset=True))
    return OwnerSalonResponse(**salon)


@router.post(
    "/me/complete-profile",
    response_model=OwnerSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete owner salon profile",
)
async def complete_profile(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> OwnerSalonResponse:
    """Mark the owner salon as complete."""

    salon = await _use_cases(session).complete_profile(actor)
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


# ── Images ────────────────────────────────────────────────────────────────────


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
)
async def delete_image(
    image_id: str,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    """Reject image deletion until the schema supports soft delete."""

    await _use_cases(session).delete_image(actor, image_id)
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
    """Reject holiday deletion until the schema supports soft delete."""

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
) -> ServiceResponse:
    """Create owner salon service."""

    row = await _use_cases(session).create_service(actor, payload.model_dump())
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
) -> ServiceResponse:
    """Update owner salon service."""

    row = await _use_cases(session).update_service(actor, service_id, payload.model_dump(exclude_unset=True))
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
) -> ServiceResponse:
    """Soft-delete owner salon service."""

    row = await _use_cases(session).deactivate_service(actor, service_id)
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
) -> StaffResponse:
    """Create owner salon staff."""

    row = await _use_cases(session).create_staff(actor, payload.model_dump())
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
) -> StaffResponse:
    """Update owner salon staff."""

    row = await _use_cases(session).update_staff(actor, staff_id, payload.model_dump(exclude_unset=True))
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
) -> StaffResponse:
    """Soft-delete owner salon staff."""

    row = await _use_cases(session).deactivate_staff(actor, staff_id)
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
