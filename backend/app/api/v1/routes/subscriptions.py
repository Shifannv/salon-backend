"""Admin subscription management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, require_role
from app.api.v1.schemas.subscription import (
    ManualSubscriptionCreateRequest,
    PlanCreateRequest,
    PlanResponse,
    PlanUpdateRequest,
    SubscriptionEventResponse,
    SubscriptionResponse,
)
from app.application.use_cases.subscription import (
    SalonSubscriptionUseCases,
    SubscriptionPlanUseCases,
)
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.subscription_repository import (
    SalonSubscriptionRepo,
    SubscriptionEventRepo,
    SubscriptionPlanRepo,
)

router = APIRouter()


def _plan_uc(session: AsyncSession) -> SubscriptionPlanUseCases:
    return SubscriptionPlanUseCases(SubscriptionPlanRepo(session))


def _sub_uc(session: AsyncSession) -> SalonSubscriptionUseCases:
    return SalonSubscriptionUseCases(
        SalonSubscriptionRepo(session), SubscriptionEventRepo(session)
    )


# ── Plans ────────────────────────────────────────────────────────────────────


@router.get(
    "/subscription-plans",
    response_model=list[PlanResponse],
    status_code=status.HTTP_200_OK,
    summary="List subscription plans (admin)",
)
async def list_plans(
    include_inactive: bool = False,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[PlanResponse]:
    rows = await _plan_uc(session).list_plans(actor, include_inactive=include_inactive)
    return [PlanResponse(**row) for row in rows]


@router.post(
    "/subscription-plans",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create subscription plan",
)
async def create_plan(
    payload: PlanCreateRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> PlanResponse:
    row = await _plan_uc(session).create_plan(actor, payload.model_dump())
    return PlanResponse(**row)


@router.patch(
    "/subscription-plans/{plan_id}",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Update subscription plan",
)
async def update_plan(
    plan_id: UUID,
    payload: PlanUpdateRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> PlanResponse:
    row = await _plan_uc(session).update_plan(
        actor, str(plan_id), payload.model_dump(exclude_unset=True)
    )
    return PlanResponse(**row)


@router.post(
    "/subscription-plans/{plan_id}/deactivate",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate subscription plan",
)
async def deactivate_plan(
    plan_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> PlanResponse:
    row = await _plan_uc(session).deactivate_plan(actor, str(plan_id))
    return PlanResponse(**row)


# ── Salon subscriptions ─────────────────────────────────────────────────────


@router.get(
    "/salons/{salon_id}/subscription",
    response_model=SubscriptionResponse | None,
    status_code=status.HTTP_200_OK,
    summary="View a salon's subscription (admin)",
)
async def get_salon_subscription(
    salon_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SubscriptionResponse | None:
    row = await _sub_uc(session).get_salon_subscription(actor, str(salon_id))
    return SubscriptionResponse(**row) if row else None


@router.post(
    "/salons/{salon_id}/subscription/test",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a test subscription (admin, manual activation only)",
    description="Creates a subscription record for testing. "
    "This is NOT payment activation — no external provider is called. "
    "Label: manual/test activation.",
)
async def create_test_subscription(
    salon_id: UUID,
    payload: ManualSubscriptionCreateRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SubscriptionResponse:
    row = await _sub_uc(session).create_test_subscription(
        actor,
        {
            "salon_id": str(salon_id),
            "plan_id": payload.plan_id,
            "status": payload.status,
            "starts_at": payload.starts_at,
            "current_period_start": payload.current_period_start,
            "current_period_end": payload.current_period_end,
        },
    )
    return SubscriptionResponse(**row)


@router.post(
    "/subscriptions/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel subscription (admin)",
)
async def cancel_subscription(
    subscription_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SubscriptionResponse:
    row = await _sub_uc(session).cancel_subscription(actor, str(subscription_id))
    return SubscriptionResponse(**row)


@router.post(
    "/subscriptions/{subscription_id}/suspend",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Suspend subscription (admin)",
)
async def suspend_subscription(
    subscription_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SubscriptionResponse:
    row = await _sub_uc(session).suspend_subscription(actor, str(subscription_id))
    return SubscriptionResponse(**row)


# ── Events ───────────────────────────────────────────────────────────────────


@router.get(
    "/subscription-events",
    response_model=list[SubscriptionEventResponse],
    status_code=status.HTTP_200_OK,
    summary="List subscription events (admin)",
)
async def list_events(
    subscription_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[SubscriptionEventResponse]:
    rows = await _sub_uc(session).list_events(
        actor, subscription_id=subscription_id, limit=limit, offset=offset
    )
    return [SubscriptionEventResponse(**row) for row in rows]
