"""Hourly R2 cleanup, scheduled by the media-cleanup Compose service."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from app.application.use_cases.media_cleanup import retire_unreferenced_media
from app.core.config import settings
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.media.health import touch
from app.infrastructure.r2.storage import R2StorageGateway

logger = logging.getLogger(__name__)


async def sweep_media(*, max_candidates: int | None = None, stop_at: float | None = None,
                      fail_on_errors: bool = False, resume_after: str | None = None,
                      checkpoint: Callable[[str | None], Awaitable[None]] | None = None) -> int:
    if not settings.r2_bucket:
        return 0
    storage = R2StorageGateway(settings)
    storage._assert_configured()
    async with AsyncSessionLocal() as session:
        if not await PlatformRepository(session).media_reference_guards_installed():
            raise RuntimeError("Media cleanup requires reviewed migration 0020_media_reference_guards")
    started = time.perf_counter()
    candidates = deleted = failures = 0
    completed = True
    last_path = resume_after
    source = storage.cleanup_candidates(after_key=resume_after) if resume_after else storage.cleanup_candidates()
    async for path in source:
        # Stop between candidates only. Cancelling an executor-backed deletion
        # can release the publication lock while its storage thread still runs.
        if ((max_candidates is not None and candidates >= max_candidates)
                or (stop_at is not None and time.monotonic() >= stop_at)):
            completed = False
            break
        candidates += 1
        try:
            async with AsyncSessionLocal() as session:
                deleted += await retire_unreferenced_media(
                    PlatformRepository(session), storage, settings.r2_bucket, path,
                )
                await session.commit()
        except Exception as exc:
            failures += 1
            # Leave the object in place and retry on the next sweep.
            logger.warning("Media cleanup candidate deferred error_type=%s", type(exc).__name__)
        last_path = path
    logger.info(
        "Media cleanup sweep candidates=%d deleted=%d failures=%d duration_seconds=%.3f",
        candidates, deleted, failures, time.perf_counter() - started,
    )
    touch(candidates, deleted, failures)
    if checkpoint is not None:
        # Persist progress even past referenced/unmarked/failed objects. Reset
        # after a complete traversal so earlier or failed objects are revisited.
        await checkpoint(None if completed else last_path)
    if failures and fail_on_errors:
        raise RuntimeError("Media cleanup candidates failed; retry on the next scheduled pass")
    return deleted


async def run_forever() -> None:
    while True:
        try:
            await sweep_media()
        except Exception as exc:
            # Exception messages may include provider payloads or credentials.
            logger.error("Media cleanup sweep failed error_type=%s", type(exc).__name__)
        await asyncio.sleep(settings.media_cleanup_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
