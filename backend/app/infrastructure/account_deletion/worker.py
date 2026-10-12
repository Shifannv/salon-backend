"""Durable account-erasure worker, run by the account-deletion Compose service."""

import asyncio
import logging
import sys

from app.application.use_cases.account_erasure import AccountErasureService
from app.core.config import Settings, settings
from app.core.exceptions import PaymentProviderNotConfiguredError
from app.infrastructure.account_deletion.health import touch
from app.infrastructure.cache.redis import init_redis_cache
from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.payments.resolver import get_payment_resolver
from app.infrastructure.r2.storage import R2StorageGateway
from app.infrastructure.supabase.auth_admin import SupabaseAuthAdminGateway

logger = logging.getLogger(__name__)

_LOCAL_ENVIRONMENTS = {"local", "test"}


def storage_is_required(cfg: Settings) -> bool:
    """Outside local/test an erasure worker without object storage cannot do its job."""

    return cfg.environment not in _LOCAL_ENVIRONMENTS


def validate_worker_configuration(cfg: Settings) -> list[str]:
    """Everything the erasure steps need, checked BEFORE the first request is claimed.

    Previously a missing R2 bucket was discovered at the media step - after the database was
    already erased - and the request then retried that step for ever. Failing at start makes
    the misconfiguration loud and leaves every account untouched.
    """

    problems: list[str] = []
    if not cfg.supabase_url or not cfg.supabase_service_role_key:
        problems.append("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required to ban and delete auth users")
    r2 = {
        "R2_ACCOUNT_ID": cfg.r2_account_id,
        "R2_ACCESS_KEY_ID": cfg.r2_access_key_id,
        "R2_SECRET_ACCESS_KEY": cfg.r2_secret_access_key,
        "R2_BUCKET": cfg.r2_bucket,
        "R2_PUBLIC_URL": cfg.r2_public_url,
    }
    missing = [name for name, value in r2.items() if not value]
    if missing and (storage_is_required(cfg) or len(missing) < len(r2)):
        # Required outside local/test; in local/test a PARTIAL config is still a mistake.
        problems.append("object storage is not fully configured; missing " + ", ".join(missing))
    if cfg.payment_provider != "none":
        try:
            get_payment_resolver().resolve()
        except PaymentProviderNotConfiguredError as exc:
            problems.append(f"payment provider {cfg.payment_provider!r} cannot refund closure bookings: {exc}")
        except Exception as exc:  # adapter import/credential errors
            problems.append(f"payment provider {cfg.payment_provider!r} failed to initialise: {type(exc).__name__}")
    return problems


async def drain_account_deletions(cache, limit: int = 20) -> int:
    """Process due requests, each in fresh sessions, until none remain or the limit hits."""

    processed = 0
    resolver = get_payment_resolver()

    def gateway_for(provider: str | None):
        try:
            return resolver.for_provider(provider)
        except PaymentProviderNotConfiguredError:
            return None

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
                payment_gateway_for=gateway_for,
                refund_max_attempts=settings.account_deletion_refund_max_attempts,
                storage_required=storage_is_required(settings),
                cache_required=bool(settings.redis_url),
            )
            if not await service.process_next():
                break
        processed += 1
        touch()  # a long backlog must not look like a dead worker
    return processed


async def run_forever() -> None:
    problems = validate_worker_configuration(settings)
    if problems:
        for problem in problems:
            logger.critical("Account deletion worker misconfigured: %s", problem)
        raise SystemExit(1)
    cache = await init_redis_cache(settings.redis_url)
    while True:
        try:
            if settings.redis_url and not cache.available:
                cache = await init_redis_cache(settings.redis_url)  # Redis may have come back
            if settings.redis_url and not cache.available:
                # Do not start a destructive step the cache step could not finish: accounts
                # stay locked and intact, the heartbeat goes stale and the container alarms.
                logger.error("Redis is configured but unreachable; account erasure is paused")
            else:
                await drain_account_deletions(cache)
                touch()
        except Exception:
            logger.exception("Account deletion poll failed")
        await asyncio.sleep(settings.account_deletion_worker_poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run_forever())
    except SystemExit as exc:
        sys.exit(exc.code)
