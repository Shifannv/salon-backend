"""Super-admin routes for feature access (mounted under /admin)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, require_role
from app.api.v1.schemas.feature_access import (
    FeatureMatrixRequest,
    FeatureOverrideRequest,
    FeatureOverrideResponse,
    FeatureOverviewResponse,
    FeatureUpdateRequest,
    PlanContentRequest,
)
from app.application.use_cases.feature_access import FeatureAccessUseCases
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.feature_access_repository import FeatureAccessRepository

router = APIRouter()
KeyPath = Path(pattern=r"^[a-z][a-z0-9_]{1,63}$")


def _uc(session: AsyncSession) -> FeatureAccessUseCases:
    return FeatureAccessUseCases(FeatureAccessRepository(session))


@router.get("/features", response_model=FeatureOverviewResponse)
async def get_features(
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> FeatureOverviewResponse:
    return FeatureOverviewResponse(**await _uc(session).overview(actor))


@router.put("/features/access", response_model=FeatureOverviewResponse)
async def save_feature_matrix(
    payload: FeatureMatrixRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> FeatureOverviewResponse:
    cells = [c.model_dump() for c in payload.cells]
    return FeatureOverviewResponse(**await _uc(session).save_matrix(actor, cells))


@router.patch("/features/{key}", response_model=FeatureOverviewResponse)
async def update_feature(
    payload: FeatureUpdateRequest,
    key: str = KeyPath,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> FeatureOverviewResponse:
    return FeatureOverviewResponse(
        **await _uc(session).update_feature(actor, key, payload.label, payload.description)
    )


@router.put("/plan-content/{tier}", response_model=FeatureOverviewResponse)
async def save_plan_content(
    payload: PlanContentRequest,
    tier: Literal["growth", "premium"],
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> FeatureOverviewResponse:
    return FeatureOverviewResponse(**await _uc(session).save_plan_content(
        actor, tier, payload.headline, payload.description, payload.bullets
    ))


@router.get("/salons/{salon_id}/feature-overrides", response_model=list[FeatureOverrideResponse])
async def list_feature_overrides(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[FeatureOverrideResponse]:
    rows = await _uc(session).list_overrides(actor, str(salon_id))
    return [FeatureOverrideResponse(**r) for r in rows]


@router.put("/salons/{salon_id}/feature-overrides/{key}", response_model=list[FeatureOverrideResponse])
async def set_feature_override(
    salon_id: UUID,
    payload: FeatureOverrideRequest,
    key: str = KeyPath,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[FeatureOverrideResponse]:
    rows = await _uc(session).set_override(
        actor, str(salon_id), key, payload.enabled, payload.expires_at, payload.note
    )
    return [FeatureOverrideResponse(**r) for r in rows]


@router.delete("/salons/{salon_id}/feature-overrides/{key}", response_model=list[FeatureOverrideResponse])
async def clear_feature_override(
    salon_id: UUID,
    key: str = KeyPath,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[FeatureOverrideResponse]:
    rows = await _uc(session).clear_override(actor, str(salon_id), key)
    return [FeatureOverrideResponse(**r) for r in rows]
