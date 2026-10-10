"""Durable account-erasure worker, run by the account-deletion Compose service."""

import asyncio
import logging

from app.application.use_cases.account_erasure import AccountErasureService
from app.core.config import settings
from app.infrastructure.cache.redis import init_redis_cache
from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.r2.storage import R2StorageGateway
from app.infrastructure.supabase.auth_admin import SupabaseAuthAdminGateway

logger = logging.getLogger(__name__)


async def drain_account_deletions(cache, limit: int = 20) -> int:
    """Process due requests, each in fresh sessions, until none remain or the limit hits."""

    processed = 0
    while processed < limit:
        async with AsyncSessionLocal() as session, AsyncSessionLocal() as media_session:
            service = AccountErasureService(
                repository=SQLAccountDeletionRepository(session),
                auth_admin=SupabaseAuthAdminGateway(settings),
                storage=R2StorageGateway(settings),
                cache=cache,
                media_references=PlatformRepository(media_session),
                release_media_lock=media_session.commit,
                bucket=settings.r2_bucket,
                stale_seconds=settings.account_deletion_stale_processing_seconds,
            )
            if not await service.process_next():
                break
        processed += 1
    return processed


async def run_forever() -> None:
    cache = await init_redis_cache(settings.redis_url)
    while True:
        try:
            await drain_account_deletions(cache)
        except Exception:
            logger.exception("Account deletion poll failed")
        await asyncio.sleep(settings.account_deletion_worker_poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
