"""Customer app API routes."""

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_cache, get_current_actor
from app.api.v1.schemas.admin import CategoryResponse, SubcategoryResponse
from app.api.v1.schemas.platform import (
    ProfileResponse,
    ProfileUpdateRequest,
    PublicStaffResponse,
    SalonDetailResponse,
    SalonSummaryResponse,
    ServiceResponse,
)
from app.application.ports.cache_gateway import CacheGateway
from app.application.use_cases.platform import CustomerUseCases
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import get_session

router = APIRouter()
salons_router = APIRouter()
catalog_router = APIRouter()


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
    surface: Literal["home", "search", "all"] | None = None,
    shuffle_seed: str = Query(default="default", min_length=1, max_length=80),
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
        surface=surface,
        shuffle_seed=shuffle_seed,
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
    """List visible salons by display priority, then distance — public, no auth required.

    Services are NOT embedded. Call GET /salons/{salon_id}/services for service data.
    Use `category` to filter by service category (e.g. ?category=Hair+Cutting).
    """

    resolved_lat = lat if lat is not None else latitude
    resolved_lng = lng if lng is not None else longitude
    rows = await _use_cases(session).list_salons(
        search=search,
        city=city,
        lat=resolved_lat,
        lng=resolved_lng,
        ids=ids,
        category=category,
        surface="all",
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
    cache: CacheGateway = Depends(get_cache),
) -> SalonDetailResponse:
    """Return active completed salon details — public, no auth required."""

    cache_key = f"salon:{salon_id}:detail"
    cached = await cache.get(cache_key)
    if cached is not None:
        await _use_cases(session).assert_public_salon(salon_id)
        return SalonDetailResponse(**cached)

    salon = await _use_cases(session).get_salon(salon_id)
    await cache.set(cache_key, salon, ttl=180)
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
    cache: CacheGateway = Depends(get_cache),
) -> list[ServiceResponse]:
    """Return active customer-visible services for a salon — public, no auth required."""

    cache_key = f"salon:{salon_id}:services"
    cached = await cache.get(cache_key)
    if cached is not None:
        await _use_cases(session).assert_public_salon(salon_id)
        return [ServiceResponse(**row) for row in cached]

    rows = await _use_cases(session).list_salon_services(salon_id)
    await cache.set(cache_key, rows, ttl=180)
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
    cache: CacheGateway = Depends(get_cache),
) -> list[PublicStaffResponse]:
    """Return active staff members for a customer-visible salon — public, no auth required."""

    cache_key = f"salon:{salon_id}:staff"
    cached = await cache.get(cache_key)
    if cached is not None:
        await _use_cases(session).assert_public_salon(salon_id)
        return [PublicStaffResponse(**row) for row in cached]

    rows = await _use_cases(session).list_salon_staff(salon_id)
    await cache.set(cache_key, rows, ttl=180)
    return [PublicStaffResponse(**row) for row in rows]


# ── Public catalog endpoints (no auth — used by owner & customer apps) ────────


@catalog_router.get(
    "/categories",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List active service categories — public",
    description=(
        "Returns all active service categories ordered by sort_order. "
        "Used by the owner app to populate the category picker when creating services, "
        "and by the customer app for category-based filtering."
    ),
)
async def list_public_categories(
    session: AsyncSession = Depends(get_session),
    cache: CacheGateway = Depends(get_cache),
) -> list[CategoryResponse]:
    """Return active service categories — no authentication required."""

    cache_key = "catalog:categories:active"
    cached = await cache.get(cache_key)
    if cached is not None:
        return [CategoryResponse(**item) for item in cached]

    repo = PlatformRepository(session)
    rows = await repo.list_categories(include_inactive=False)
    results = [{**row, "id": str(row["id"])} for row in rows]
    await cache.set(cache_key, results, ttl=300)
    return [CategoryResponse(**row) for row in results]


@catalog_router.get(
    "/categories/{category_id}/subcategories",
    response_model=list[SubcategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List active subcategories for a category — public",
    description=(
        "Returns all active subcategories for the given category. "
        "Used by the owner app to let the barber pick a specific subcategory "
        "when creating or editing a service."
    ),
)
async def list_public_subcategories(
    category_id: str = Path(description="The service category UUID"),
    session: AsyncSession = Depends(get_session),
    cache: CacheGateway = Depends(get_cache),
) -> list[SubcategoryResponse]:
    """Return active subcategories for a category — no authentication required."""

    cache_key = f"catalog:subcategories:active:{category_id}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return [SubcategoryResponse(**item) for item in cached]

    repo = PlatformRepository(session)
    rows = await repo.list_subcategories(category_id, include_inactive=False)
    results = [
        {**row, "id": str(row["id"]), "category_id": str(row["category_id"])}
        for row in rows
    ]
    await cache.set(cache_key, results, ttl=300)
    return [SubcategoryResponse(**row) for row in results]
