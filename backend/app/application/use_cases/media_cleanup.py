"""Retire only unreferenced, server-processed media under a publication lock."""

from app.application.ports.media_references import MediaReferences
from app.application.ports.storage_gateway import StorageGateway
from app.core.exceptions import ValidationError


async def retire_unreferenced_media(
    references: MediaReferences, storage: StorageGateway, bucket: str, path: str,
) -> bool:
    # Fail closed for legacy/unmarked objects, missing objects and HEAD failures.
    try:
        lock_paths = await storage.retirement_lock_paths(path)
    except ValidationError:
        return False
    for key in lock_paths:
        await references.lock_media_url(storage.get_public_url(bucket, key))
    # Inventory aliases AFTER taking member locks. Any concurrent publication
    # must wait for these locks and revalidate the whole family after acquisition.
    paths = await storage.retirement_paths(path)
    if not await storage.retirement_ready(paths):
        return False
    for key in paths:
        if await references.media_url_is_referenced(storage.get_public_url(bucket, key)):
            return False
    # No eager deletion on upload/save errors. Only the retirement path owns deletes.
    for key in [key for key in paths if key != path] + [path]:
        await storage.delete_object(bucket, key)
    return True
