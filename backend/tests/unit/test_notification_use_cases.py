"""Unit tests for NotificationUseCases."""

import pytest

from app.application.use_cases.platform import NotificationUseCases
from tests.conftest import make_mock_repo, make_profile


@pytest.mark.asyncio
async def test_list_notifications_delegates():
    repo = make_mock_repo()
    repo.list_notifications.return_value = [
        {"id": "notif-001", "title": "Booking Confirmed", "read": False}
    ]
    uc = NotificationUseCases(repo)
    actor = make_profile()

    notifs = await uc.list_notifications(actor)
    assert len(notifs) == 1
    repo.list_notifications.assert_awaited_once_with(actor.id, audience=None)


@pytest.mark.asyncio
async def test_mark_read_delegates():
    repo = make_mock_repo()
    repo.mark_notification_read.return_value = {"id": "notif-001", "read": True}
    uc = NotificationUseCases(repo)
    actor = make_profile()

    result = await uc.mark_read(actor, "notif-001")
    assert result["read"] is True
    repo.mark_notification_read.assert_awaited_once_with(actor.id, "notif-001")


@pytest.mark.asyncio
async def test_mark_all_read_returns_updated_count():
    repo = make_mock_repo()
    repo.mark_all_notifications_read.return_value = 3
    uc = NotificationUseCases(repo)
    actor = make_profile()

    result = await uc.mark_all_read(actor)

    assert result == 3
    repo.mark_all_notifications_read.assert_awaited_once_with(actor.id)


@pytest.mark.asyncio
async def test_register_device_passes_actor_id():
    repo = make_mock_repo()
    repo.register_device.return_value = {"id": "dt-001", "token": "tok123", "platform": "ios"}
    uc = NotificationUseCases(repo)
    actor = make_profile(id="user-999")

    result = await uc.register_device(actor, "tok123", "ios", "iPhone 14")
    assert result["token"] == "tok123"
    repo.register_device.assert_awaited_once_with("user-999", "tok123", "ios", "iPhone 14", None)


@pytest.mark.asyncio
async def test_deactivate_device_delegates_with_actor_id():
    repo = make_mock_repo()
    uc = NotificationUseCases(repo)
    actor = make_profile(id="user-999")

    await uc.deactivate_device(actor, "tok123")
    repo.deactivate_device_for_actor.assert_awaited_once_with("user-999", "tok123")
