"""Authorize hosted objects and serialize saving their references with cleanup."""

from app.application.ports.image_processor import ImagePolicy
from app.application.ports.media_references import MediaReferences
from app.application.ports.storage_gateway import StorageGateway
from app.core.exceptions import ValidationError


async def validate_media_reference(
    references: MediaReferences, storage: StorageGateway | None, url: str | None,
    namespace: str, policy: ImagePolicy | None = None,
) -> None:
    if url is None:
        return
    if storage is None:
        raise ValidationError("Validated image storage is required to save a new photo")
    # This transaction lock remains held through the repository's reference-write commit.
    await references.lock_media_url(url)
    for member_url in sorted(set(await storage.publication_urls(url)) - {url}):
        await references.lock_media_url(member_url)
    if policy is None:
        await storage.validate_media_reference(url, namespace)
    else:
        await storage.validate_media_reference(url, namespace, policy=policy)
