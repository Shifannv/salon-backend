"""User profiles API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor
from app.api.v1.schemas.auth import ProfileResponse
from app.api.v1.schemas.platform import ProfileUpdateRequest
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


@router.get(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current profile",
)
async def get_my_profile(actor: Profile = Depends(get_current_actor)) -> ProfileResponse:
    """Return the authenticated profile."""

    return ProfileResponse(
        id=actor.id,
        role=actor.role,
        full_name=actor.full_name,
        email=actor.email,
        phone=actor.phone,
        phone_verified=actor.phone_verified,
        avatar_url=actor.avatar_url,
        is_active=actor.is_active,
    )


@router.patch(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current profile",
)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ProfileResponse:
    """Update the authenticated user's profile (e.g. phone number or full name)."""

    repo = PlatformRepository(session)
    updated = await repo.update_profile(actor.id, payload.model_dump(exclude_unset=True))
    return ProfileResponse(**updated)
