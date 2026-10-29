"""Super-admin API routes."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_admin_gateway,
    get_authenticated_session,
    get_cache,
    get_current_actor,
    get_storage_gateway,
    require_role,
)
from app.api.v1.schemas.admin import (
    AdminApproveSalonRequest,
    AdminCreateSalonRequest,
    AdminDeactivateSalonResponse,
    AdminRejectSalonRequest,
    AdminSalonOnboardingResponse,
    AdminSalonResponse,
    AdminUpdateSalonRequest,
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    LanguageResponse,
    SubcategoryCreateRequest,
    SubcategoryResponse,
    SubcategoryUpdateRequest,
)
from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.cache_gateway import CacheGateway
from app.application.use_cases.admin import AdminUseCases, CatalogAdminUseCases
from app.domain.entities.profile import Profile, Role
from app.domain.services.trial_limits import TrialLimits
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.push.outbox_worker import enqueue_and_deliver_notification

router = APIRouter()


def _admin_use_cases(session: AsyncSession, auth_admin: AuthAdminGateway) -> AdminUseCases:
    return AdminUseCases(
        PlatformRepository(session),
        auth_admin,
        notify_owner=_notify_owner,
    )


async def _notify_owner(
    *,
    user_id: UUID,
    notification_type: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Persist and push an owner notification that is not tied to a booking."""
    await enqueue_and_deliver_notification(
        user_id=str(user_id),
        booking_id=None,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data,
    )


def _catalog_use_cases(session: AsyncSession) -> CatalogAdminUseCases:
    return CatalogAdminUseCases(PlatformRepository(session), storage_gateway=get_storage_gateway())


# ── Salon management ──────────────────────────────────────────────────────────


@router.post(
    "/salons",
    response_model=AdminSalonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create salon owner and salon",
    description="Creates a Supabase Auth user and a salon in one transaction. "
                "If the salon insert fails, the auth user is banned to prevent orphans.",
)
async def create_salon(
    payload: AdminCreateSalonRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AdminSalonResponse:
    """Create a new salon owner account and their salon."""

    salon = await _admin_use_cases(session, auth_admin).create_salon_owner(
        actor=actor,
        email=str(payload.email),
        password=payload.password,
        full_name=payload.full_name,
        salon_name=payload.salon_name,
        timezone=payload.timezone,
    )
    return AdminSalonResponse(**salon)


@router.get(
    "/salons",
    response_model=list[AdminSalonResponse],
    status_code=status.HTTP_200_OK,
    summary="List all salons (admin)",
)
async def list_salons(
    search: str | None = None,
    approval_status: Literal["pending", "approved", "rejected"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> list[AdminSalonResponse]:
    """List all salons with owner info — paginated."""

    rows = await _admin_use_cases(session, auth_admin).list_salons(
        actor, search=search, limit=limit, offset=offset, approval_status=approval_status
    )
    return [AdminSalonResponse(**row) for row in rows]


@router.get("/salons/{salon_id}", response_model=AdminSalonResponse, status_code=200)
async def get_salon(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AdminSalonResponse:
    salon = await _admin_use_cases(session, auth_admin).get_salon(actor, str(salon_id))
    return AdminSalonResponse(**salon)


@router.get(
    "/salons/{salon_id}/onboarding",
    response_model=AdminSalonOnboardingResponse,
    status_code=200,
)
async def get_salon_onboarding(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AdminSalonOnboardingResponse:
    salon = await _admin_use_cases(session, auth_admin).get_onboarding(actor, str(salon_id))
    return AdminSalonOnboardingResponse(**salon)


@router.post("/salons/{salon_id}/approve", response_model=AdminSalonResponse, status_code=200)
async def approve_salon(
    salon_id: UUID,
    background_tasks: BackgroundTasks,
    payload: AdminApproveSalonRequest | None = Body(default=None),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AdminSalonResponse:
    salon = await _admin_use_cases(session, auth_admin).approve_salon(
        actor, str(salon_id), background_tasks,
        trial_limits=TrialLimits(payload.trial_days, payload.trial_booking_limit) if payload else None,
    )
    return AdminSalonResponse(**salon)


@router.post("/salons/{salon_id}/reject", response_model=AdminSalonResponse, status_code=200)
async def reject_salon(
    salon_id: UUID,
    payload: AdminRejectSalonRequest,
    background_tasks: BackgroundTasks,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AdminSalonResponse:
    salon = await _admin_use_cases(session, auth_admin).reject_salon(
        actor, str(salon_id), payload.rejection_reason, background_tasks
    )
    return AdminSalonResponse(**salon)


@router.patch(
    "/salons/{salon_id}",
    response_model=AdminSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Update salon (admin)",
)
async def update_salon(
    salon_id: UUID,
    payload: AdminUpdateSalonRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AdminSalonResponse:
    """Update admin-editable salon fields."""

    salon = await _admin_use_cases(session, auth_admin).update_salon(
        actor, str(salon_id), payload.model_dump(exclude_unset=True)
    )
    return AdminSalonResponse(**salon)


@router.post(
    "/salons/{salon_id}/deactivate",
    response_model=AdminDeactivateSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate salon and ban owner",
)
async def deactivate_salon(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
    cache: CacheGateway = Depends(get_cache),
) -> AdminDeactivateSalonResponse:
    """Soft-delete the salon and ban the owner's Supabase Auth account."""

    result = await _admin_use_cases(session, auth_admin).deactivate_salon(actor, str(salon_id))
    await cache.delete_prefix(f"salon:{salon_id}:")
    await cache.delete_prefix("walkin:qr:")
    return AdminDeactivateSalonResponse(**result)


@router.post(
    "/salons/{salon_id}/reactivate",
    response_model=AdminSalonResponse,
    status_code=status.HTTP_200_OK,
    summary="Reactivate salon and owner",
)
async def reactivate_salon(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
    cache: CacheGateway = Depends(get_cache),
) -> AdminSalonResponse:
    """Restore an inactive salon and lift the owner's Supabase Auth ban."""

    salon = await _admin_use_cases(session, auth_admin).reactivate_salon(
        actor, str(salon_id)
    )
    await cache.delete_prefix(f"salon:{salon_id}:")
    await cache.delete_prefix("walkin:qr:")
    return AdminSalonResponse(**salon)


# ── Service catalog management ────────────────────────────────────────────────


@router.get(
    "/catalog/categories",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List service categories (admin)",
)
async def list_categories(
    include_inactive: bool = False,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[CategoryResponse]:
    """List all service categories including inactive ones."""

    rows = await _catalog_use_cases(session).list_categories(actor, include_inactive)
    return [CategoryResponse(**row) for row in rows]


@router.post(
    "/catalog/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create service category",
)
async def create_category(
    payload: CategoryCreateRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> CategoryResponse:
    """Create a new service category."""

    row = await _catalog_use_cases(session).create_category(actor, payload.model_dump())
    await cache.delete("catalog:categories:active")
    return CategoryResponse(**row)


@router.patch(
    "/catalog/categories/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update service category",
)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdateRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> CategoryResponse:
    """Update a service category."""

    row = await _catalog_use_cases(session).update_category(
        actor, str(category_id), payload.model_dump(exclude_unset=True)
    )
    await cache.delete("catalog:categories:active")
    await cache.delete(f"catalog:subcategories:active:{category_id}")
    return CategoryResponse(**row)


@router.post(
    "/catalog/categories/{category_id}/deactivate",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate service category",
)
async def deactivate_category(
    category_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> CategoryResponse:
    """Soft-delete a service category."""

    row = await _catalog_use_cases(session).deactivate_category(actor, str(category_id))
    await cache.delete("catalog:categories:active")
    await cache.delete(f"catalog:subcategories:active:{category_id}")
    return CategoryResponse(**row)


@router.get(
    "/catalog/categories/{category_id}/subcategories",
    response_model=list[SubcategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List subcategories (admin)",
)
async def list_subcategories(
    category_id: UUID,
    include_inactive: bool = False,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[SubcategoryResponse]:
    """List all subcategories for a category."""

    rows = await _catalog_use_cases(session).list_subcategories(
        actor, str(category_id), include_inactive
    )
    return [SubcategoryResponse(**row) for row in rows]


@router.post(
    "/catalog/subcategories",
    response_model=SubcategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create service subcategory",
)
async def create_subcategory(
    payload: SubcategoryCreateRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> SubcategoryResponse:
    """Create a new service subcategory."""

    row = await _catalog_use_cases(session).create_subcategory(actor, payload.model_dump())
    await cache.delete_prefix("catalog:subcategories:")
    return SubcategoryResponse(**row)


@router.patch(
    "/catalog/subcategories/{subcategory_id}",
    response_model=SubcategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update service subcategory",
)
async def update_subcategory(
    subcategory_id: UUID,
    payload: SubcategoryUpdateRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> SubcategoryResponse:
    """Update a service subcategory."""

    row = await _catalog_use_cases(session).update_subcategory(
        actor, str(subcategory_id), payload.model_dump(exclude_unset=True)
    )
    await cache.delete_prefix("catalog:subcategories:")
    return SubcategoryResponse(**row)


@router.post(
    "/catalog/subcategories/{subcategory_id}/deactivate",
    response_model=SubcategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate service subcategory",
)
async def deactivate_subcategory(
    subcategory_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    cache: CacheGateway = Depends(get_cache),
) -> SubcategoryResponse:
    """Soft-delete a service subcategory."""

    row = await _catalog_use_cases(session).deactivate_subcategory(actor, str(subcategory_id))
    await cache.delete_prefix("catalog:subcategories:")
    return SubcategoryResponse(**row)


@router.get(
    "/catalog/languages",
    response_model=list[LanguageResponse],
    status_code=status.HTTP_200_OK,
    summary="List supported languages",
)
async def list_languages(
    session: AsyncSession = Depends(get_authenticated_session),
    _actor: Profile = Depends(get_current_actor),
) -> list[LanguageResponse]:
    """Return the languages reference table (accessible to all authenticated users)."""

    rows = await _catalog_use_cases(session).list_available_languages()
    return [LanguageResponse(**row) for row in rows]
