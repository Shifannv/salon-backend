"""One bounded maintenance pass for Cloud Run Jobs; never starts a polling loop.

Run only after reviewing the job's image, configuration, data effects and schedule.
Payment/subscription queues are excluded. Owner account erasure can still require
refunds through its existing workflow and must not run before those prerequisites
are reviewed. Time budgets are cooperative: never cancel an in-flight operation.
"""

import argparse
import asyncio
import json
import time
from collections.abc import Awaitable, Callable

TASKS = ("account-deletion", "email", "media-cleanup")


async def drain_queue(deliver: Callable[[], Awaitable[bool]], limit: int, stop_at: float) -> dict:
    attempted = 0
    for _ in range(limit):
        if time.monotonic() >= stop_at:
            return {"attempted": attempted, "budget_exhausted": True}
        if not await deliver():
            break
        attempted += 1
    return {"attempted": attempted, "budget_exhausted": time.monotonic() >= stop_at}


async def run_pass(task: str, limit: int, stop_at: float) -> dict:
    if task not in TASKS or not 1 <= limit <= 100:
        raise ValueError("Unknown task or invalid batch limit")

    from app.core.config import settings

    if task == "email":
        from app.infrastructure.email.resend import ResendEmailGateway
        from app.infrastructure.email.worker import deliver_once

        if not ResendEmailGateway(settings).enabled:
            raise RuntimeError("Email delivery is not configured")
        return await drain_queue(deliver_once, limit, stop_at)

    if task == "media-cleanup":
        from app.infrastructure.cache.redis import init_redis_cache
        from app.infrastructure.media.cleanup_worker import sweep_media
        from app.infrastructure.r2.storage import R2StorageGateway

        R2StorageGateway(settings)._assert_configured()
        if not settings.redis_url:
            raise RuntimeError("Bounded media cleanup requires durable enumeration checkpoints")
        cache = await init_redis_cache(settings.redis_url)
        if not await cache.ping():
            raise RuntimeError("Media cleanup checkpoint storage is unreachable")
        key = "maintenance:media-cursor:v1"
        saved = await cache.get(key)
        if saved is not None and (not isinstance(saved, dict)
                                  or (saved.get("after") is not None and not isinstance(saved["after"], str))):
            raise RuntimeError("Invalid media enumeration checkpoint")

        async def checkpoint(after):
            value = {"after": after}
            await cache.set(key, value, ttl=7 * 24 * 3600)
            if await cache.get(key) != value:
                raise RuntimeError("Media enumeration checkpoint was not saved")

        deleted = await sweep_media(max_candidates=limit, stop_at=stop_at, fail_on_errors=True,
                                    resume_after=(saved or {}).get("after"), checkpoint=checkpoint)
        return {"deleted": deleted, "budget_exhausted": time.monotonic() >= stop_at}

    from app.infrastructure.account_deletion.worker import (
        drain_account_deletions,
        validate_worker_configuration,
    )
    from app.infrastructure.cache.redis import init_redis_cache

    if validate_worker_configuration(settings):
        raise RuntimeError("Account deletion prerequisites are incomplete")
    cache = await init_redis_cache(settings.redis_url)
    if settings.redis_url and not await cache.ping():
        raise RuntimeError("Account deletion requires reachable configured Redis")
    async def attempt_one():
        return bool(await drain_account_deletions(cache, limit=1))

    return await drain_queue(attempt_one, limit, stop_at)


async def run_job(task: str, limit: int, timeout_seconds: int) -> dict:
    if task not in TASKS or not 1 <= limit <= 100 or not 1 <= timeout_seconds <= 900:
        raise ValueError("Invalid maintenance job bounds")
    # Load resources only for an explicitly selected, validated task.
    from app.infrastructure.cache.redis import close_redis_cache
    from app.infrastructure.db.session import engine

    try:
        return await run_pass(task, limit, time.monotonic() + timeout_seconds)
    finally:
        try:
            await close_redis_cache()
        finally:
            await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=TASKS)
    parser.add_argument("--limit", type=int, default=20,
                        help="Maximum queue attempts or media candidates (1–100)")
    parser.add_argument("--timeout-seconds", type=int, default=240,
                        help="Cooperative budget (1–900); finish in-flight work before stopping")
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(run_job(args.task, args.limit, args.timeout_seconds))
    except Exception as error:
        # Never emit provider payloads, SQL diagnostics, tokens or request contents.
        print(json.dumps({"task": args.task, "status": "failed", "error_type": type(error).__name__}))
        return 1
    print(json.dumps({"task": args.task, "status": "pass_completed", **result,
                      "item_outcomes": "Inspect durable queues; attempts include failed or deferred items"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
