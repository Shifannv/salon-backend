"""Owner salon holiday routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_session,
    get_current_actor,
)
from app.api.v1.routes.owner_common import owner_use_cases
from app.api.v1.schemas.platform import (
    HolidayCreateRequest,
    HolidayResponse,
)
from app.domain.entities.profile import Profile

router = APIRouter()


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

    rows = await owner_use_cases(session).list_holidays(actor)
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

    row = await owner_use_cases(session).create_holiday(actor, payload.model_dump())
    return HolidayResponse(**row)


@router.delete(
    "/me/holidays/{holiday_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete owner salon holiday",
)
async def delete_holiday(
    holiday_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    """Soft-delete a holiday owned by the authenticated owner's salon."""

    await owner_use_cases(session).delete_holiday(actor, str(holiday_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
