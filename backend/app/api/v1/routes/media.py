"""Authenticated customer avatar upload route."""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.application.ports.image_processor import ImagePolicy
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media import MAX_IMAGE_BYTES, UploadAvatar
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.media.pillow_processor import PillowImageProcessor

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
    url = await UploadAvatar(
        PlatformRepository(session), storage, PillowImageProcessor(settings.image_max_pixels),
        ImagePolicy(settings.image_avatar_dimension, settings.image_avatar_max_bytes),
    ).execute(
        actor, data, image.content_type or "", settings.r2_bucket or "salon-images",
    )
    return AvatarResponse(avatar_url=url)


@router.put("/media/uploads/{token}", response_model=None, status_code=204)
async def upload_signed_image(
    token: str, request: Request, storage: StorageGateway = Depends(get_storage_gateway),
) -> None:
    # A short-lived signed capability is issued only after existing actor/ownership checks.
    mime = request.headers.get("content-type", "")
    storage.validate_upload_token(token, mime)
    length = request.headers.get("content-length")
    if length is not None:
        try:
            size = int(length)
        except ValueError as exc:
            raise ValidationError("Invalid upload length") from exc
        if size < 1 or size > MAX_IMAGE_BYTES:
            raise ValidationError("Image must be between 1 byte and 5 MB")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_IMAGE_BYTES:
            raise ValidationError("Image must be between 1 byte and 5 MB")
        data.extend(chunk)
    await storage.accept_upload(token, bytes(data), mime)
