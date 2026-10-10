"""Authenticated avatars: process before storage; clean up failed publication."""

import logging
from typing import Protocol
from uuid import uuid4

from app.application.ports.image_processor import ImagePolicy, ImageProcessor
from app.application.ports.storage_gateway import StorageGateway
from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Profile, Role

MAX_IMAGE_BYTES = 5 * 1024 * 1024
_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
logger = logging.getLogger(__name__)


class AvatarRepository(Protocol):
    async def update_profile(self, profile_id: str, values: dict) -> dict: ...


class UploadAvatar:
    def __init__(self, repository: AvatarRepository, storage: StorageGateway,
                 processor: ImageProcessor, policy: ImagePolicy = ImagePolicy(512, 500 * 1024)):
        self.repository = repository
        self.storage = storage
        self.processor = processor
        self.policy = policy

    async def execute(self, actor: Profile, data: bytes, content_type: str, bucket: str) -> str:
        if not actor.is_active or actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")
        if content_type not in _EXTENSIONS:
            raise ValidationError("Avatar must be JPEG, PNG or WebP")
        processed = await self.processor.process_async(data, content_type, self.policy)
        path = f"avatars/{actor.id}/{uuid4().hex}.{_EXTENSIONS[content_type]}"
        try:
            url = await self.storage.upload_bytes(bucket, path, processed, content_type)
            await self.repository.update_profile(actor.id, {"avatar_url": url})
        except Exception:
            try:
                await self.storage.delete_object(bucket, path)
            except Exception:
                logger.warning("Avatar cleanup failed")
            raise
        return url
