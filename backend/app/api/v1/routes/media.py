"""Authenticated customer avatar upload route."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
from app.api.v1.schemas.image_family import AvatarResponse, ImageFamilyResponse
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media import MAX_IMAGE_BYTES, UploadAvatar
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.media.pillow_processor import PillowImageProcessor

router = APIRouter()


@router.post("/customer/profile/avatar", response_model=AvatarResponse, status_code=200,
             openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {
                 "schema": {"type": "object", "required": ["image"], "properties": {
                     "image": {"type": "string", "format": "binary"}}}}}}})
async def upload_avatar(
    request: Request,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    storage: StorageGateway = Depends(get_storage_gateway),
) -> AvatarResponse:
    # Admission middleware bounds the entire request before parsing/spooling.
    async with request.form(max_files=1, max_fields=0) as form:
        image = form.get("image")
        if not isinstance(image, UploadFile) or len(form.multi_items()) != 1:
            raise ValidationError("Provide exactly one image file")
        data = await image.read(MAX_IMAGE_BYTES + 1)
        mime = image.content_type or ""
    result = await UploadAvatar(
        PlatformRepository(session), storage, PillowImageProcessor(settings.image_max_pixels),
    ).execute_family(
        actor, data, mime, settings.media_bucket,
    )
    return AvatarResponse(avatar_url=result["public_url"], **{k: v for k, v in result.items() if k != "public_url"})


@router.put("/media/uploads/{token}", response_model=None, status_code=204)
async def upload_signed_image(
    token: str, request: Request, response: Response, storage: StorageGateway = Depends(get_storage_gateway),
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
    result = await storage.accept_upload(token, bytes(data), mime)
    response.headers["X-Image-Family-ID"] = result["family_id"]
    response.headers["Cache-Control"] = "no-store"
    # The object is already stored: deriving the link must never turn this into an error.
    try:
        result_url = storage.get_result_url(token)
    except ValidationError:
        result_url = None
    if result_url:
        response.headers["Link"] = f'<{result_url}>; rel="describedby"'


@router.get("/media/results/{token}", response_model=ImageFamilyResponse, status_code=200)
async def get_image_family(token: str, response: Response,
                           storage: StorageGateway = Depends(get_storage_gateway)) -> ImageFamilyResponse:
    """Read variant metadata with a read-only token; it cannot upload."""
    response.headers["Cache-Control"] = "no-store"
    return ImageFamilyResponse(**await storage.upload_result(token))
