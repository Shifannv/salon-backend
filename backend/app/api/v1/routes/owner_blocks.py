"""Owner blocked-slot routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_session,
    get_current_actor,
)
from app.api.v1.routes.owner_common import owner_use_cases
from app.api.v1.schemas.platform import (
    BlockedSlotCreateRequest,
    BlockedSlotResponse,
)
from app.domain.entities.profile import Profile

router = APIRouter()


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

    rows = await owner_use_cases(session).list_blocked_slots(actor)
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

    row = await owner_use_cases(session).create_blocked_slot(actor, payload.model_dump())
    return BlockedSlotResponse(**row)


@router.delete(
    "/me/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a blocked slot",
)
async def delete_blocked_slot(
    block_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    """Hard-delete a blocked slot. Blocked slots have no is_active column in the schema."""

    await owner_use_cases(session).delete_blocked_slot(actor, str(block_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
