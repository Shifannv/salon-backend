"""Unit tests for OwnerUseCases — Phase 3 features."""

import pytest

from app.application.use_cases.platform import OwnerUseCases
from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Role
from tests.conftest import make_mock_repo, make_owner, make_profile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SALON = {
    "id": "salon-001",
    "owner_id": "owner-001",
    "name": "Scissors & Style",
    "timezone": "Asia/Kolkata",
    "is_active": True,
}


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_my_salon_requires_owner_or_staff():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.get_my_salon(customer)


@pytest.mark.asyncio
async def test_get_my_salon_owner_ok():
    repo = make_mock_repo()
    repo.get_owner_salon.return_value = SALON
    uc = OwnerUseCases(repo)
    owner = make_owner()

    salon = await uc.get_my_salon(owner)
    assert salon["id"] == "salon-001"
    repo.get_owner_salon.assert_awaited_once_with(owner.id)


# ---------------------------------------------------------------------------
# Images — soft delete not supported
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_image_raises_validation_error():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    owner = make_owner()

    with pytest.raises(ValidationError, match="soft delete"):
        await uc.delete_image(owner, "image-001")


# ---------------------------------------------------------------------------
# Holidays — deletion not supported
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_holiday_raises_validation_error():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    owner = make_owner()

    with pytest.raises(ValidationError, match="soft delete"):
        await uc.delete_holiday(owner, "holiday-001")


# ---------------------------------------------------------------------------
# Staff languages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_staff_service_languages_delegates():
    repo = make_mock_repo()
    repo.list_staff_service_languages.return_value = [
        {"code": "en", "name": "English"},
        {"code": "ml", "name": "Malayalam"},
    ]
    uc = OwnerUseCases(repo)
    owner = make_owner()

    langs = await uc.list_staff_service_languages(owner, "staff-001", "ss-001")
    assert len(langs) == 2
    repo.list_staff_service_languages.assert_awaited_once_with(
        owner.id, "staff-001", "ss-001"
    )


@pytest.mark.asyncio
async def test_set_staff_service_languages_delegates():
    repo = make_mock_repo()
    repo.set_staff_service_languages.return_value = [{"code": "hi", "name": "Hindi"}]
    uc = OwnerUseCases(repo)
    owner = make_owner()

    result = await uc.set_staff_service_languages(owner, "staff-001", "ss-001", ["hi"])
    assert result[0]["code"] == "hi"
    repo.set_staff_service_languages.assert_awaited_once_with(
        owner.id, "staff-001", "ss-001", ["hi"]
    )


@pytest.mark.asyncio
async def test_list_staff_service_languages_requires_owner():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.list_staff_service_languages(customer, "staff-001", "ss-001")


# ---------------------------------------------------------------------------
# Blocked slots
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_blocked_slots_delegates():
    repo = make_mock_repo()
    repo.list_blocked_slots.return_value = [
        {"id": "block-001", "block_type": "leave"}
    ]
    uc = OwnerUseCases(repo)
    owner = make_owner()

    slots = await uc.list_blocked_slots(owner)
    assert len(slots) == 1
    repo.list_blocked_slots.assert_awaited_once_with(owner.id)


@pytest.mark.asyncio
async def test_create_blocked_slot_delegates():
    repo = make_mock_repo()
    repo.create_blocked_slot.return_value = {"id": "block-001", "block_type": "break"}
    uc = OwnerUseCases(repo)
    owner = make_owner()

    from datetime import datetime

    values = {
        "start_datetime": datetime(2025, 6, 1, 12, 0),
        "end_datetime": datetime(2025, 6, 1, 13, 0),
        "block_type": "break",
    }
    slot = await uc.create_blocked_slot(owner, values)
    assert slot["block_type"] == "break"
    repo.create_blocked_slot.assert_awaited_once_with(owner.id, values)


@pytest.mark.asyncio
async def test_delete_blocked_slot_delegates():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    owner = make_owner()

    await uc.delete_blocked_slot(owner, "block-001")
    repo.delete_blocked_slot.assert_awaited_once_with(owner.id, "block-001")


@pytest.mark.asyncio
async def test_list_blocked_slots_requires_owner():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.list_blocked_slots(customer)
