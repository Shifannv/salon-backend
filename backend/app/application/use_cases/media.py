"""Authenticated avatars: process before storage; clean up failed publication."""

from typing import Protocol

from app.application.ports.image_processor import ImageProcessor
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media_publication import validate_media_reference
from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Profile, Role

MAX_IMAGE_BYTES = 5 * 1024 * 1024
_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class AvatarRepository(Protocol):
    async def update_profile(self, profile_id: str, values: dict) -> dict: ...

    async def lock_media_url(self, url: str) -> None: ...


class UploadAvatar:
    def __init__(self, repository: AvatarRepository, storage: StorageGateway,
                 processor: ImageProcessor):
        self.repository = repository
        self.storage = storage
        self.processor = processor

    async def execute(self, actor: Profile, data: bytes, content_type: str, bucket: str) -> str:
        result = await self.execute_family(actor, data, content_type, bucket)
        return result["public_url"]

    async def execute_family(self, actor: Profile, data: bytes, content_type: str, bucket: str) -> dict:
        if not actor.is_active or actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")
        if content_type not in _EXTENSIONS:
            raise ValidationError("Avatar must be JPEG, PNG or WebP")
        processed = await self.processor.process_family_async(data, content_type, "avatar")
        result = await self.storage.upload_processed_family(bucket, f"avatars/{actor.id}/", processed)
        url = result["public_url"]
        await validate_media_reference(self.repository, self.storage, url, f"avatars/{actor.id}/")
        await self.repository.update_profile(actor.id, {"avatar_url": url})
        # Cleanup runs after committed reference checks. A failed/ambiguous commit
        # must never trigger deletion of an object that might now be referenced.
        return result
