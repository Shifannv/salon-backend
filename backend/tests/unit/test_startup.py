"""Cold-start guards: deferred imports and concurrent warm-up in the lifespan."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import main

BACKEND = Path(__file__).resolve().parents[2]

# Each is needed only by some requests and costs Cloud Run cold-start time if loaded
# at import (measured 2026-10-20, docs/verification/cloud-run-startup-profile-2026-10-20.md).
DEFERRED = ("httpx", "jose", "cryptography", "PIL", "segno")


def test_app_import_does_not_load_request_only_libraries() -> None:
    code = (
        "import json, sys; import app.main; "
        f"print(json.dumps([m for m in {DEFERRED!r} if m in sys.modules]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, env=os.environ.copy(),
        capture_output=True, text=True, timeout=120, check=True,
    )
    assert json.loads(result.stdout.strip().splitlines()[-1]) == []


def test_app_import_leaves_garbage_collection_enabled() -> None:
    code = "import gc, app.main; print(gc.isenabled(), gc.get_freeze_count() > 0)"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, env=os.environ.copy(),
        capture_output=True, text=True, timeout=120, check=True,
    )
    assert result.stdout.strip().splitlines()[-1] == "True True"


async def test_lifespan_warms_database_and_cache_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    running: set[str] = set()
    overlapped = asyncio.Event()

    def step(name: str):
        async def run() -> None:
            running.add(name)
            if running == {"db", "cache"}:
                overlapped.set()
            await asyncio.wait_for(overlapped.wait(), timeout=1)

        return run

    monkeypatch.setattr(main, "_warm_database", step("db"))
    monkeypatch.setattr(main, "_init_cache", step("cache"))

    async with main.lifespan(main.app):
        assert overlapped.is_set()


async def test_one_failed_warm_up_does_not_stop_the_other(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenSession:
        async def __aenter__(self):
            raise ConnectionError("database down")

        async def __aexit__(self, *exc: object) -> None:
            return None

    redis_urls: list[object] = []

    async def fake_init(url: object) -> None:
        redis_urls.append(url)

    monkeypatch.setattr("app.infrastructure.db.session.AsyncSessionLocal", BrokenSession)
    monkeypatch.setattr("app.infrastructure.cache.redis.init_redis_cache", fake_init)

    async with main.lifespan(main.app):
        pass

    assert redis_urls == [main.settings.redis_url]
