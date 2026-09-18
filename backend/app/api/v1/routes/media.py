"""Authenticated customer avatar upload route."""

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media import MAX_IMAGE_BYTES, UploadAvatar
from app.core.config import settings
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

router = APIRouter()


class AvatarResponse(BaseModel):
    avatar_url: str


@router.post("/customer/profile/avatar", response_model=AvatarResponse, status_code=200)
async def upload_avatar(
    image: UploadFile = File(...),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage: StorageGateway = Depends(get_storage_gateway),
) -> AvatarResponse:
    try:
        data = await image.read(MAX_IMAGE_BYTES + 1)
    finally:
        await image.close()
    url = await UploadAvatar(PlatformRepository(session), storage).execute(
        actor, data, image.content_type or "", settings.r2_bucket or "salon-images",
    )
    return AvatarResponse(avatar_url=url)
