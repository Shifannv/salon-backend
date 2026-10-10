"""Hourly R2 cleanup, scheduled by the media-cleanup Compose service."""

import asyncio
import logging

from app.application.use_cases.media_cleanup import retire_unreferenced_media
from app.core.config import settings
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.r2.storage import R2StorageGateway

logger = logging.getLogger(__name__)


async def sweep_media() -> int:
    if not settings.r2_bucket:
        return 0
    storage = R2StorageGateway(settings)
    storage._assert_configured()
    async with AsyncSessionLocal() as session:
        if not await PlatformRepository(session).media_reference_guards_installed():
            raise RuntimeError("Media cleanup requires reviewed migration 0020_media_reference_guards")
    deleted = 0
    async for path in storage.cleanup_candidates():
        try:
            async with AsyncSessionLocal() as session:
                deleted += await retire_unreferenced_media(
                    PlatformRepository(session), storage, settings.r2_bucket, path,
                )
                await session.commit()
        except Exception:
            # Leave the object in place and retry on the next sweep.
            logger.warning("Media cleanup deferred after storage or reference-check failure")
    return deleted


async def run_forever() -> None:
    while True:
        try:
            deleted = await sweep_media()
            logger.info("Media cleanup removed %s unreferenced managed objects", deleted)
        except Exception:
            logger.exception("Media cleanup sweep failed")
        await asyncio.sleep(settings.media_cleanup_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
