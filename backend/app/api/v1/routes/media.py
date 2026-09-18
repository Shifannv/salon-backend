"""Upload routes for ImageKit-compatible PUTs and customer avatars."""

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media import MAX_IMAGE_BYTES, UploadAvatar, validate_image
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.imagekit.storage import ImageKitStorageGateway

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


@router.put("/media/uploads/{ticket}", response_model=None, status_code=204)
async def upload_imagekit(ticket: str, request: Request) -> Response:
    if settings.storage_provider != "imagekit":
        raise NotFoundError("Upload endpoint is not enabled")
    storage = ImageKitStorageGateway(settings)
    claims = storage.verify_ticket(ticket)
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != claims["content_type"]:
        raise ValidationError("Content-Type must match the upload URL request")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValidationError("Image must not exceed 5 MB")
    validate_image(bytes(data), content_type)
    await storage.upload_bytes("", claims["path"], bytes(data), content_type)
    return Response(status_code=204)
