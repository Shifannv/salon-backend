"""Cleanup observability tests using local heartbeat files and mocked gateways."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.media import cleanup_worker, health


def test_heartbeat_missing_stale_failed_and_successful(tmp_path):
    path = tmp_path / "heartbeat.json"
    assert not health.is_healthy(path)
    health.touch(3, 2, 0, path)
    payload = json.loads(path.read_text())
    assert payload["candidates"] == 3 and payload["deleted"] == 2
    assert payload["last_success_time"] == payload["last_completed_time"]
    now = payload["last_completed_time"]
    assert health.is_healthy(path, now=now + 10, max_age=20)
    assert not health.is_healthy(path, now=now + 21, max_age=20)
    assert not health.is_healthy(path, now=now - 1, max_age=20)
    health.touch(4, 0, 1, path)
    assert not health.is_healthy(path)
    assert json.loads(path.read_text())["last_success_time"] == payload["last_success_time"]


@pytest.mark.parametrize("contents", ["garbage", "[]", "{}", '{"last_completed_time": "nan"}'])
def test_malformed_heartbeat_unhealthy(tmp_path, contents):
    path = tmp_path / "heartbeat.json"
    path.write_text(contents)
    assert not health.is_healthy(path)


def test_dynamic_health_age(monkeypatch):
    monkeypatch.setenv("MEDIA_CLEANUP_INTERVAL_SECONDS", "7200")
    assert health.max_age_seconds() == 7800
    monkeypatch.setenv("MEDIA_CLEANUP_INTERVAL_SECONDS", "invalid")
    assert health.max_age_seconds() == 4200


def setup_sweep(monkeypatch, tmp_path, *, guards=True):
    path = tmp_path / "worker.json"
    monkeypatch.setenv("MEDIA_CLEANUP_HEARTBEAT_FILE", str(path))
    monkeypatch.setattr(cleanup_worker.settings, "r2_bucket", "local-images")
    gateway = MagicMock()

    async def candidates():
        yield "avatars/user/test-a.webp"
        yield "avatars/user/test-b.webp"

    gateway.cleanup_candidates = candidates
    monkeypatch.setattr(cleanup_worker, "R2StorageGateway", lambda settings: gateway)
    repository = AsyncMock()
    repository.media_reference_guards_installed.return_value = guards
    monkeypatch.setattr(cleanup_worker, "PlatformRepository", lambda session: repository)
    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    monkeypatch.setattr(cleanup_worker, "AsyncSessionLocal", factory)
    return path, gateway, session


async def test_sweep_heartbeat_records_success_counts(monkeypatch, tmp_path, caplog):
    path, _, session = setup_sweep(monkeypatch, tmp_path)
    monkeypatch.setattr(cleanup_worker, "retire_unreferenced_media", AsyncMock(side_effect=[True, False]))
    with caplog.at_level("INFO"):
        assert await cleanup_worker.sweep_media() == 1
    payload = json.loads(path.read_text())
    assert (payload["candidates"], payload["deleted"], payload["failures"]) == (2, 1, 0)
    assert health.is_healthy(path)
    assert session.commit.await_count == 2
    assert "candidates=2 deleted=1 failures=0 duration_seconds=" in caplog.text


async def test_sweep_failures_are_counted_without_logging_provider_message(monkeypatch, tmp_path, caplog):
    path, _, _ = setup_sweep(monkeypatch, tmp_path)
    retire = AsyncMock(side_effect=[RuntimeError("private-provider-detail"), True, True, False])
    monkeypatch.setattr(cleanup_worker, "retire_unreferenced_media", retire)
    assert await cleanup_worker.sweep_media() == 1
    payload = json.loads(path.read_text())
    assert (payload["candidates"], payload["deleted"], payload["failures"]) == (2, 1, 1)
    assert not health.is_healthy(path)
    assert "error_type=RuntimeError" in caplog.text
    assert "private-provider-detail" not in caplog.text
    assert await cleanup_worker.sweep_media() == 1
    assert health.is_healthy(path)


async def test_missing_guards_or_listing_failure_never_touch_heartbeat(monkeypatch, tmp_path):
    path, gateway, _ = setup_sweep(monkeypatch, tmp_path, guards=False)
    with pytest.raises(RuntimeError, match="0020"):
        await cleanup_worker.sweep_media()
    assert not path.exists()
    path, gateway, _ = setup_sweep(monkeypatch, tmp_path)

    async def failing_candidates():
        raise RuntimeError("listing unavailable")
        yield  # pragma: no cover

    gateway.cleanup_candidates = failing_candidates
    with pytest.raises(RuntimeError, match="listing unavailable"):
        await cleanup_worker.sweep_media()
    assert not path.exists()
