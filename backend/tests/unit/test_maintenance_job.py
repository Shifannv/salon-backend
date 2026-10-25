"""Bounded passes stop between work items and preserve in-flight storage locks."""

import asyncio
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.infrastructure import maintenance_job as job


async def test_email_pass_stops_at_limit_with_a_continuous_backlog():
    deliver = AsyncMock(return_value=True)
    assert (await job.drain_queue(deliver, 3, time.monotonic() + 20))["attempted"] == 3
    assert deliver.await_count == 3


async def test_email_pass_stops_on_an_empty_queue():
    deliver = AsyncMock(side_effect=[True, False])
    assert (await job.drain_queue(deliver, 20, time.monotonic() + 20))["attempted"] == 1
    assert deliver.await_count == 2


async def test_email_failure_is_not_reported_as_a_successful_empty_queue():
    with pytest.raises(RuntimeError):
        await job.drain_queue(AsyncMock(side_effect=RuntimeError("private provider payload")), 20, time.monotonic() + 20)


@pytest.mark.parametrize(("task", "limit", "seconds"), [
    ("payments", 20, 240), ("email", 0, 240), ("email", 101, 240),
    ("email", 20, 0), ("email", 20, 901),
])
async def test_invalid_bounds_fail_before_work(task, limit, seconds, monkeypatch):
    work = AsyncMock()
    monkeypatch.setattr(job, "run_pass", work)
    with pytest.raises(ValueError):
        await job.run_job(task, limit, seconds)
    work.assert_not_awaited()


async def test_budget_does_not_cancel_in_flight_work_and_closes_resources(monkeypatch):
    from app.infrastructure.cache import redis
    from app.infrastructure.db import session

    completed = asyncio.Event()

    async def slow(*_args):
        await asyncio.sleep(1.05)
        completed.set()
        return {"attempted": 1, "budget_exhausted": True}

    close, dispose = AsyncMock(), AsyncMock()
    monkeypatch.setattr(job, "run_pass", slow)
    monkeypatch.setattr(redis, "close_redis_cache", close)
    monkeypatch.setattr(session, "engine", SimpleNamespace(dispose=dispose))
    result = await job.run_job("email", 20, 1)
    assert result["budget_exhausted"] and completed.is_set()
    close.assert_awaited_once()
    dispose.assert_awaited_once()


def test_cli_failure_redacts_provider_details(monkeypatch, capsys):
    monkeypatch.setattr(job, "run_job", AsyncMock(side_effect=RuntimeError("secret-private-value")))
    assert job.main(["email"]) == 1
    output = capsys.readouterr().out
    assert '"status": "failed"' in output
    assert "RuntimeError" in output and "secret-private-value" not in output


async def test_expired_budget_starts_no_queue_attempt():
    deliver = AsyncMock(return_value=True)
    result = await job.drain_queue(deliver, 20, time.monotonic() - 1)
    assert result == {"attempted": 0, "budget_exhausted": True}
    deliver.assert_not_awaited()


def media_fixture(monkeypatch):
    from app.infrastructure.media import cleanup_worker as worker

    active = []
    commits = []

    class Session:
        async def __aenter__(self):
            active.append(self)
            return self

        async def __aexit__(self, *_args):
            active.remove(self)

        async def commit(self):
            commits.append(True)

    class Storage:
        def __init__(self, _settings):
            pass

        def _assert_configured(self):
            pass

        async def cleanup_candidates(self, *, after_key=None):
            for key in ("synthetic-a", "synthetic-b"):
                if after_key is None or key > after_key:
                    yield key

    monkeypatch.setattr(worker.settings, "r2_bucket", "synthetic-only")
    monkeypatch.setattr(worker, "AsyncSessionLocal", Session)
    monkeypatch.setattr(worker, "PlatformRepository", lambda _: SimpleNamespace(
        media_reference_guards_installed=AsyncMock(return_value=True)))
    monkeypatch.setattr(worker, "R2StorageGateway", Storage)
    monkeypatch.setattr(worker, "touch", lambda *_args: None)
    return worker, active, commits


async def test_media_budget_keeps_session_until_threaded_operation_and_commit_finish(monkeypatch):
    worker, active, commits = media_fixture(monkeypatch)
    started, release = threading.Event(), threading.Event()

    def blocking_delete():
        started.set()
        assert release.wait(timeout=5)
        assert active, "publication session was released before storage finished"
        return 1

    async def retire(*_args):
        return await asyncio.to_thread(blocking_delete)

    monkeypatch.setattr(worker, "retire_unreferenced_media", retire)
    task = asyncio.create_task(worker.sweep_media(max_candidates=20, stop_at=time.monotonic() + 0.05))
    try:
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.005)
        assert started.is_set()
        await asyncio.sleep(0.06)
        assert active and not task.done() and not commits
    finally:
        release.set()
    assert await task == 1
    assert commits == [True] and not active


async def test_scheduled_media_pass_reports_candidate_failure(monkeypatch):
    worker, _active, _commits = media_fixture(monkeypatch)
    monkeypatch.setattr(worker, "retire_unreferenced_media", AsyncMock(side_effect=RuntimeError("private")))
    with pytest.raises(RuntimeError, match="Media cleanup candidates failed"):
        await worker.sweep_media(max_candidates=1, fail_on_errors=True)


async def test_media_checkpoint_advances_past_referenced_objects_and_resets(monkeypatch):
    worker, _active, _commits = media_fixture(monkeypatch)
    retire = AsyncMock(side_effect=[0, 1])
    save = AsyncMock()
    monkeypatch.setattr(worker, "retire_unreferenced_media", retire)
    assert await worker.sweep_media(max_candidates=1, checkpoint=save) == 0
    save.assert_awaited_once_with("synthetic-a")
    save.reset_mock()
    assert await worker.sweep_media(max_candidates=1, resume_after="synthetic-a", checkpoint=save) == 1
    save.assert_awaited_once_with(None)
    assert retire.await_count == 2


async def test_media_failed_candidate_advances_cursor_before_reporting_failure(monkeypatch):
    worker, _active, _commits = media_fixture(monkeypatch)
    save = AsyncMock()
    monkeypatch.setattr(worker, "retire_unreferenced_media", AsyncMock(side_effect=RuntimeError("private")))
    with pytest.raises(RuntimeError):
        await worker.sweep_media(max_candidates=1, fail_on_errors=True, checkpoint=save)
    save.assert_awaited_once_with("synthetic-a")


async def test_r2_media_resume_skips_previous_prefixes_and_uses_start_after(monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.infrastructure.r2.storage import R2StorageGateway

    config = SimpleNamespace(media_cleanup_grace_seconds=60, r2_bucket="synthetic")
    gateway = R2StorageGateway(config)
    calls = []

    def listing(params):
        calls.append(params)
        return {"Contents": [{"Key": params["Prefix"] + "next", "LastModified": datetime.now(UTC) - timedelta(days=2)}]}

    monkeypatch.setattr(gateway, "_list_sync", listing)
    keys = [key async for key in gateway.cleanup_candidates(after_key="salon-images/previous")]
    assert keys == ["salon-images/next", "staff-photos/next"]
    assert calls[0]["StartAfter"] == "salon-images/previous"
    assert "StartAfter" not in calls[1]


async def test_media_job_refuses_unreachable_checkpoint_store_before_sweeping(monkeypatch):
    from app.core.config import settings
    from app.infrastructure.cache import redis
    from app.infrastructure.media import cleanup_worker
    from app.infrastructure.r2.storage import R2StorageGateway

    monkeypatch.setattr(settings, "redis_url", "redis://synthetic.invalid")
    monkeypatch.setattr(R2StorageGateway, "_assert_configured", lambda _: None)
    monkeypatch.setattr(redis, "init_redis_cache", AsyncMock(return_value=SimpleNamespace(ping=AsyncMock(return_value=False))))
    sweep = AsyncMock()
    monkeypatch.setattr(cleanup_worker, "sweep_media", sweep)
    with pytest.raises(RuntimeError, match="checkpoint storage is unreachable"):
        await job.run_pass("media-cleanup", 20, time.monotonic() + 20)
    sweep.assert_not_awaited()
