"""Admin insight routes — salons needing a subscription decision, per-salon analytics, bulk offers."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, require_role
from app.api.v1.schemas.admin_insights import (
    BulkPlanPriceRequest,
    BulkPlanPriceResponse,
    SalonAnalyticsResponse,
    SalonSubscriptionRow,
    SalonSubscriptionSummary,
    SubscriptionState,
)
from app.application.use_cases.admin_insights import AdminInsightsUseCases
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.admin_insights_repository import AdminInsightsRepo
from app.infrastructure.db.repositories.subscription_repository import SubscriptionPlanRepo

router = APIRouter()


def _uc(session: AsyncSession) -> AdminInsightsUseCases:
    return AdminInsightsUseCases(AdminInsightsRepo(session), SubscriptionPlanRepo(session))


@router.get(
    "/salon-subscriptions",
    response_model=list[SalonSubscriptionRow],
    status_code=status.HTTP_200_OK,
    summary="Salons that need a subscription decision (admin)",
    description=(
        "lapsed: had a subscription that is over or suspended. none: never subscribed and no free "
        "trial is running. ending_soon: a paid period, free trial or payment grace period ends "
        "within `within_days`. "
        "Without `state`, all three are returned."
    ),
)
async def list_salon_subscriptions(
    state: SubscriptionState | None = None,
    within_days: int = Query(7, ge=1, le=90),
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> list[SalonSubscriptionRow]:
    rows = await _uc(session).list_salon_subscriptions(
        actor, state=state, within_days=within_days, search=search, limit=limit, offset=offset
    )
    return [SalonSubscriptionRow(**row) for row in rows]


@router.get(
    "/salon-subscriptions/summary",
    response_model=SalonSubscriptionSummary,
    status_code=status.HTTP_200_OK,
    summary="Counts for each subscription state across all salons (admin)",
)
async def salon_subscription_summary(
    within_days: int = Query(7, ge=1, le=90),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonSubscriptionSummary:
    return SalonSubscriptionSummary(
        **await _uc(session).subscription_summary(actor, within_days=within_days)
    )


@router.get(
    "/salons/{salon_id}/analytics",
    response_model=SalonAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="A salon's bookings and income over a date range (admin)",
    description=(
        "Both dates are required and chosen by the admin (Asia/Kolkata calendar days, inclusive). "
        "The end date cannot be in the future."
    ),
)
async def salon_analytics(
    salon_id: UUID,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> SalonAnalyticsResponse:
    data = await _uc(session).salon_analytics(actor, str(salon_id), date_from, date_to)
    return SalonAnalyticsResponse(**data)


@router.put(
    "/plan-prices/bulk",
    response_model=BulkPlanPriceResponse,
    status_code=status.HTTP_200_OK,
    summary="Give the same plan offer to many salons (admin)",
    description=(
        "Same rules as a single salon offer. Applied to every salon or to none. Safe to repeat: "
        "sending it again sets the same values."
    ),
)
async def bulk_set_plan_price(
    payload: BulkPlanPriceRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> BulkPlanPriceResponse:
    data = await _uc(session).bulk_set_plan_price(
        actor,
        salon_ids=payload.salon_ids,
        plan_id=payload.plan_id,
        price=payload.price_amount,
        offer_discount_percent=payload.offer_discount_percent,
        valid_until=payload.valid_until,
    )
    return BulkPlanPriceResponse(**data)
