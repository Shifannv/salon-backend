"""Customer app API routes."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.platform import (
    ProfileResponse,
    ProfileUpdateRequest,
    PublicStaffResponse,
    SalonDetailResponse,
    SalonSummaryResponse,
    ServiceResponse,
)
from app.application.use_cases.platform import CustomerUseCases
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import get_session

router = APIRouter()
salons_router = APIRouter()


def _use_cases(session: AsyncSession) -> CustomerUseCases:
    return CustomerUseCases(PlatformRepository(session))


@router.get(
    "/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer profile",
)
async def get_profile(actor: Profile = Depends(get_current_actor)) -> ProfileResponse:
    """Return the authenticated customer profile."""

    return ProfileResponse(**asdict(actor))


@router.patch(
    "/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update customer profile",
)
async def update_profile(
    payload: ProfileUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ProfileResponse:
    """Update the authenticated customer's profile."""

    profile = await _use_cases(session).update_profile(actor, payload.model_dump(exclude_unset=True))
    return ProfileResponse(**profile)


@salons_router.get(
    "/salons",
    response_model=list[SalonSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List customer-visible salons",
)
async def list_salons(
    search: str | None = None,
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    ids: list[str] | None = Query(default=None),
    category: str | None = Query(
        default=None,
        description=(
            "Filter salons to those offering services in this category. "
            "Matched case-insensitively against service_categories.name, "
            "e.g. 'Hair Cutting', 'Beard Care', 'Facial'."
        ),
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[SalonSummaryResponse]:
    """List active completed salons — public, no auth required.

    Services are NOT embedded. Call GET /salons/{salon_id}/services for service data.
    Use `category` to filter by service category (e.g. ?category=Hair+Cutting).
    """

    rows = await _use_cases(session).list_salons(
        search=search,
        city=city,
        lat=lat,
        lng=lng,
        ids=ids,
        category=category,
        limit=limit,
        offset=offset,
    )
    return [SalonSummaryResponse(**row) for row in rows]


@salons_router.get(
    "/salons/nearby",
    response_model=list[SalonSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List nearby salons",
)
async def nearby_salons(
    # Accept both 'lat/lng' (internal) and 'latitude/longitude' (frontend alias)
    lat: float | None = Query(default=None, alias="lat"),
    lng: float | None = Query(default=None, alias="lng"),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    search: str | None = None,
    city: str | None = None,
    ids: list[str] | None = Query(default=None),
    category: str | None = Query(
        default=None,
        description=(
            "Filter salons to those offering services in this category. "
            "Matched case-insensitively against service_categories.name, "
            "e.g. 'Hair Cutting', 'Beard Care', 'Facial'."
        ),
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[SalonSummaryResponse]:
    """List active completed salons ordered by distance — public, no auth required.

    Services are NOT embedded. Call GET /salons/{salon_id}/services for service data.
    Use `category` to filter by service category (e.g. ?category=Hair+Cutting).
    """

    resolved_lat = lat or latitude
    resolved_lng = lng or longitude
    rows = await _use_cases(session).list_salons(
        search=search,
        city=city,
        lat=resolved_lat,
        lng=resolved_lng,
        ids=ids,
        category=category,
        limit=limit,
        offset=offset,
    )
    return [SalonSummaryResponse(**row) for row in rows]


@salons_router.get(
    "/salons/{salon_id}",
    response_model=SalonDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get salon details",
)
async def get_salon(
    salon_id: str,
    session: AsyncSession = Depends(get_session),
) -> SalonDetailResponse:
    """Return active completed salon details — public, no auth required."""

    salon = await _use_cases(session).get_salon(salon_id)
    return SalonDetailResponse(**salon)


@salons_router.get(
    "/salons/{salon_id}/services",
    response_model=list[ServiceResponse],
    status_code=status.HTTP_200_OK,
    summary="List salon services",
)
async def list_salon_services(
    salon_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[ServiceResponse]:
    """Return active customer-visible services for a salon — public, no auth required."""

    rows = await _use_cases(session).list_salon_services(salon_id)
    return [ServiceResponse(**row) for row in rows]


@salons_router.get(
    "/salons/{salon_id}/staff",
    response_model=list[PublicStaffResponse],
    status_code=status.HTTP_200_OK,
    summary="List salon staff",
)
async def list_salon_staff(
    salon_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[PublicStaffResponse]:
    """Return active staff members for a customer-visible salon — public, no auth required."""

    rows = await _use_cases(session).list_salon_staff(salon_id)
    return [PublicStaffResponse(**row) for row in rows]
