"""User profiles API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.api.v1.schemas.auth import ProfileResponse
from app.api.v1.schemas.platform import (
    ImageUploadUrlRequest,
    ImageUploadUrlResponse,
    ProfileUpdateRequest,
)
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.platform import CustomerUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


def _bucket() -> str:
    """Return the configured R2 bucket name, falling back to the default."""
    return settings.r2_bucket or "salon-images"


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
    storage_gateway: StorageGateway = Depends(get_storage_gateway),
) -> ProfileResponse:
    """Update the authenticated user's profile (e.g. phone number or full name).

    When ``avatar_url`` is changed and the previous avatar was stored in R2,
    the old object is deleted from R2 best-effort before returning.
    """

    repo = PlatformRepository(session)
    updated = await CustomerUseCases(repo, storage_gateway=storage_gateway).update_profile(
        actor,
        payload.model_dump(exclude_unset=True),
        bucket=_bucket(),
        r2_public_base=settings.r2_public_url or "",
    )
    return ProfileResponse(**updated)


@router.post(
    "/me/avatar-upload-url",
    response_model=ImageUploadUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get presigned R2 upload URL for profile avatar",
    description=(
        "Returns a short-lived presigned PUT URL and the resulting public URL for "
        "uploading a profile avatar directly to Cloudflare R2.\n\n"
        "Available to all authenticated roles (customer, owner, staff).\n\n"
        "**Upload flow:**\n"
        "1. Call this endpoint to get `upload_url` and `public_url`.\n"
        "2. `PUT <upload_url>` with the image binary and `Content-Type: <your_mime_type>` header.\n"
        "3. Call `PATCH /profiles/me` with `{ \"avatar_url\": \"<public_url>\" }` to persist."
    ),
)
async def get_avatar_upload_url(
    payload: ImageUploadUrlRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage_gateway: StorageGateway = Depends(get_storage_gateway),
) -> ImageUploadUrlResponse:
    """Generate a presigned R2 PUT URL for a direct profile avatar upload."""

    result = await CustomerUseCases(PlatformRepository(session), storage_gateway=storage_gateway).get_avatar_upload_url(
        actor,
        content_type=payload.content_type,
        filename=payload.filename,
        bucket=_bucket(),
    )
    return ImageUploadUrlResponse(**result)
