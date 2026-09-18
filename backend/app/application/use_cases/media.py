"""Image validation and authenticated avatar uploads."""

from typing import Protocol
from uuid import uuid4

from app.application.ports.storage_gateway import StorageGateway
from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Profile, Role

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image(data: bytes, content_type: str) -> str:
    """Check size and file signatures instead of trusting the supplied MIME type."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValidationError("Image must be between 1 byte and 5 MB")
    signatures = {
        "image/jpeg": (data.startswith(b"\xff\xd8\xff"), "jpg"),
        "image/png": (data.startswith(b"\x89PNG\r\n\x1a\n"), "png"),
        "image/webp": (data[:4] == b"RIFF" and data[8:12] == b"WEBP", "webp"),
        "image/heic": (data[4:8] == b"ftyp" and data[8:12] in
                       {b"heic", b"heix", b"hevc", b"hevx", b"mif1"}, "heic"),
        "image/heif": (data[4:8] == b"ftyp" and data[8:12] in
                       {b"heic", b"heix", b"mif1", b"msf1"}, "heif"),
    }
    valid, extension = signatures.get(content_type, (False, ""))
    if not valid:
        raise ValidationError("Unsupported image or content type does not match file")
    return extension


class AvatarRepository(Protocol):
    async def update_profile(self, profile_id: str, values: dict) -> dict: ...


class UploadAvatar:
    def __init__(self, repository: AvatarRepository, storage: StorageGateway) -> None:
        self.repository = repository
        self.storage = storage

    async def execute(self, actor: Profile, data: bytes, content_type: str, bucket: str) -> str:
        if not actor.is_active or actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValidationError("Avatar must be JPEG, PNG or WebP")
        extension = validate_image(data, content_type)
        path = f"avatars/{actor.id}/{uuid4().hex}.{extension}"
        url = await self.storage.upload_bytes(bucket, path, data, content_type)
        await self.repository.update_profile(actor.id, {"avatar_url": url})
        return url
