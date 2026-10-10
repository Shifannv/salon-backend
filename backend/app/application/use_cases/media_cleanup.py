"""Retire only unreferenced, server-processed media under a publication lock."""

from app.application.ports.media_references import MediaReferences
from app.application.ports.storage_gateway import StorageGateway
from app.core.exceptions import ValidationError


async def retire_unreferenced_media(
    references: MediaReferences, storage: StorageGateway, bucket: str, path: str,
) -> bool:
    url = storage.get_public_url(bucket, path)
    await references.lock_media_url(url)
    # Fail closed for legacy/unmarked objects, missing objects and HEAD failures.
    try:
        await storage.validate_media_reference(url, path.rsplit("/", 1)[0] + "/")
    except ValidationError:
        return False
    if await references.media_url_is_referenced(url):
        return False
    await storage.delete_object(bucket, path)
    return True
