"""Outbox delivery retries provider failures and completes successful sends."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.push import outbox_worker


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True])
async def test_outbox_worker_marks_delivery_or_retry(
    monkeypatch: pytest.MonkeyPatch, failed: bool
) -> None:
    session = MagicMock()

    @asynccontextmanager
    async def session_factory():
        yield session

    repository = MagicMock()
    repository.get_notification_outbox_event = AsyncMock(
        return_value={
            "notification_id": "notification-1",
            "user_id": "customer-1",
        }
    )
    repository.notification_has_failed_delivery = AsyncMock(return_value=failed)
    repository.mark_notification_outbox_processed = AsyncMock()
    repository.mark_notification_outbox_retry = AsyncMock()
    gateway = MagicMock()
    gateway.fan_out = AsyncMock()

    monkeypatch.setattr(outbox_worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(outbox_worker, "PlatformRepository", lambda _session: repository)
    monkeypatch.setattr(outbox_worker, "FCMGateway", lambda _settings, _session: gateway)

    await outbox_worker.deliver_notification_outbox_event("outbox-1")

    gateway.fan_out.assert_awaited_once_with("notification-1", "customer-1")
    if failed:
        repository.mark_notification_outbox_retry.assert_awaited_once()
        repository.mark_notification_outbox_processed.assert_not_awaited()
    else:
        repository.mark_notification_outbox_processed.assert_awaited_once_with(
            "outbox-1"
        )
        repository.mark_notification_outbox_retry.assert_not_awaited()
