"""Identity/readiness verification without startup, network or database access."""
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from app.api.v1.routes import health
from app.core import build_info
from app.core.config import settings


@pytest.mark.parametrize("content,expected", [(None, "unknown"), ("injected", "unknown"), ("a" * 40, "a" * 40)])
def test_build_commit_is_file_backed_not_runtime_environment(tmp_path, monkeypatch, content, expected):
    path = tmp_path / "build-commit"
    if content is not None:
        path.write_text(content)
    monkeypatch.setattr(build_info, "COMMIT_FILE", path)
    monkeypatch.setenv("SOURCE_COMMIT", "b" * 40)
    assert build_info.source_commit() == expected


async def test_public_version_is_baked_and_not_cached(tmp_path, monkeypatch):
    path = tmp_path / "build-commit"
    path.write_text("a" * 40)
    monkeypatch.setattr(build_info, "COMMIT_FILE", path)
    app = FastAPI()
    app.include_router(health.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://local.test") as client:
        result = await client.get("/version")
    assert result.status_code == 200 and result.json() == {"version": "0.1.0", "commit_sha": "a" * 40}
    assert result.headers["Cache-Control"] == "no-store"


async def test_readiness_dependency_failure_is_not_process_success(monkeypatch):
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("synthetic unavailable dependency")
    cache = AsyncMock()
    with pytest.raises(Exception, match="Database is unavailable"):
        await health.readiness(session=session, cache=cache)
    cache.ping.assert_not_awaited()


async def test_readiness_uses_only_injected_dependency_probes(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", "redis://synthetic")
    session, cache = AsyncMock(), AsyncMock()
    cache.available = True
    cache.ping.return_value = True
    result = await health.readiness(session=session, cache=cache)
    assert result.status == "ok" and session.execute.await_count == 1 and cache.ping.await_count == 1
