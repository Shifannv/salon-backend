"""Unit tests for OwnerUseCases — Phase 3 features."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.api.v1.schemas.platform import HolidayResponse
from app.application.use_cases.platform import OwnerUseCases
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Role
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
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


@pytest.mark.asyncio
async def test_complete_profile_sends_final_payload_to_repository():
    repo = make_mock_repo()
    repo.complete_owner_salon.return_value = {**SALON, "profile_completed": True}
    uc = OwnerUseCases(repo)
    owner = make_owner()
    payload = {"name": "Luxe Salon", "address": "MG Road"}

    salon = await uc.complete_profile(owner, payload)

    assert salon["profile_completed"] is True
    repo.complete_owner_salon.assert_awaited_once_with(owner.id, payload)


def test_service_response_normalizes_uuid_ids_for_api_schema():
    row = {
        "id": uuid4(),
        "salon_id": uuid4(),
        "subcategory_id": uuid4(),
        "name": "Taper Fade",
        "description": None,
        "duration_minutes": 45,
        "price": 500,
        "is_active": True,
        "created_at": None,
        "updated_at": None,
    }

    service = PlatformRepository._service_response(row)

    assert isinstance(service["id"], str)
    assert isinstance(service["salon_id"], str)
    assert isinstance(service["subcategory_id"], str)


def test_staff_response_normalizes_uuid_ids_for_api_schema():
    row = {
        "id": uuid4(),
        "salon_id": uuid4(),
        "profile_id": uuid4(),
        "name": "Ameen",
        "photo_url": None,
        "specialization": "Barber",
        "working_hours": None,
        "is_active": True,
        "created_at": None,
        "updated_at": None,
    }

    staff = PlatformRepository._staff_response(row)

    assert isinstance(staff["id"], str)
    assert isinstance(staff["salon_id"], str)
    assert isinstance(staff["profile_id"], str)


def test_staff_service_response_normalizes_uuid_ids_for_api_schema():
    row = {
        "id": uuid4(),
        "staff_id": uuid4(),
        "service_id": uuid4(),
        "duration_minutes": None,
        "price_override": None,
        "specialization": None,
        "is_active": True,
        "created_at": None,
        "updated_at": None,
    }

    assignment = PlatformRepository._staff_service_response(row)

    assert isinstance(assignment["id"], str)
    assert isinstance(assignment["staff_id"], str)
    assert isinstance(assignment["service_id"], str)


def test_holiday_response_converts_database_uuid_ids_to_strings():
    holiday_id = uuid4()
    salon_id = uuid4()

    response = HolidayResponse(
        id=holiday_id,
        salon_id=salon_id,
        holiday_date=date(2026, 1, 1),
        title="New Year",
        is_recurring=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert response.id == str(holiday_id)
    assert response.salon_id == str(salon_id)


# ---------------------------------------------------------------------------
# Images — soft delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_image_soft_deletes_and_calls_r2():
    """delete_image soft-deletes the DB row and removes the R2 object."""
    from unittest.mock import AsyncMock

    repo = make_mock_repo()
    repo.get_owner_salon.return_value = SALON
    # Simulate the DB returning the deleted image's URL
    deleted_url = "https://pub-test.r2.dev/salon-images/salon-001/abc.jpeg"
    repo.delete_salon_image = AsyncMock(return_value=deleted_url)

    storage = AsyncMock()
    storage.delete_object = AsyncMock()

    uc = OwnerUseCases(repo, storage_gateway=storage)
    owner = make_owner()

    await uc.delete_image(
        owner,
        image_id="image-001",
        bucket="salon-images",
        r2_public_base="https://pub-test.r2.dev",
    )

    repo.delete_salon_image.assert_awaited_once_with(owner.id, "image-001")
    storage.delete_object.assert_awaited_once_with(
        "salon-images", "salon-images/salon-001/abc.jpeg"
    )


@pytest.mark.asyncio
async def test_delete_image_raises_not_found_when_missing():
    """delete_image raises NotFoundError if the image does not exist."""
    from unittest.mock import AsyncMock

    from app.core.exceptions import NotFoundError

    repo = make_mock_repo()
    repo.get_owner_salon.return_value = SALON
    repo.delete_salon_image = AsyncMock(return_value=None)  # row not found

    uc = OwnerUseCases(repo)
    owner = make_owner()

    with pytest.raises(NotFoundError, match="Image not found"):
        await uc.delete_image(
            owner,
            image_id="missing-id",
            bucket="salon-images",
            r2_public_base="https://pub-test.r2.dev",
        )


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_holiday_delegates_to_repository():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    owner = make_owner()

    await uc.delete_holiday(owner, "holiday-001")

    repo.delete_holiday.assert_awaited_once_with(owner.id, "holiday-001")


# ---------------------------------------------------------------------------
# Staff languages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_staff_services_delegates():
    repo = make_mock_repo()
    repo.list_staff_services.return_value = [
        {"id": "ss-001", "staff_id": "staff-001", "service_id": "svc-001"}
    ]
    uc = OwnerUseCases(repo)
    owner = make_owner()

    services = await uc.list_staff_services(owner, "staff-001")

    assert len(services) == 1
    repo.list_staff_services.assert_awaited_once_with(owner.id, "staff-001")


@pytest.mark.asyncio
async def test_list_staff_services_requires_owner():
    repo = make_mock_repo()
    uc = OwnerUseCases(repo)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.list_staff_services(customer, "staff-001")


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


# ---------------------------------------------------------------------------
# Image upload URL
# ---------------------------------------------------------------------------


class _FakeStorageGateway:
    """Minimal in-memory StorageGateway stub for upload use case tests."""

    async def get_upload_url(self, bucket: str, path: str, content_type: str = "image/jpeg") -> str:
        return f"https://presigned.example.com/{path}"

    def get_public_url(self, bucket: str, path: str) -> str:
        return f"https://pub.example.com/{path}"

    async def delete_object(self, bucket: str, path: str) -> None:
        pass


@pytest.mark.asyncio
async def test_get_image_upload_url_returns_upload_result():
    repo = make_mock_repo()
    repo.get_owner_salon.return_value = SALON
    gw = _FakeStorageGateway()
    uc = OwnerUseCases(repo, storage_gateway=gw)
    owner = make_owner()

    result = await uc.get_image_upload_url(
        owner,
        content_type="image/jpeg",
        filename="cover.jpg",
        bucket="salon-images",
    )

    assert "upload_url" in result
    assert "public_url" in result
    assert result["expires_in"] == 300
    assert "salon-images/salon-001/" in result["upload_url"]
    assert "salon-images/salon-001/" in result["public_url"]


@pytest.mark.asyncio
async def test_get_image_upload_url_raises_when_no_gateway():
    """Calling get_image_upload_url without a gateway is a programming error."""
    repo = make_mock_repo()
    repo.get_owner_salon.return_value = SALON
    uc = OwnerUseCases(repo)  # no storage_gateway — assert guards against this
    owner = make_owner()

    with pytest.raises(AssertionError, match="storage_gateway is required for image upload"):
        await uc.get_image_upload_url(owner, content_type="image/jpeg", filename="f.jpg", bucket="salon-images")


@pytest.mark.asyncio
async def test_get_image_upload_url_raises_for_non_owner():
    repo = make_mock_repo()
    gw = _FakeStorageGateway()
    uc = OwnerUseCases(repo, storage_gateway=gw)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.get_image_upload_url(customer, content_type="image/jpeg", filename="f.jpg", bucket="salon-images")


# ---------------------------------------------------------------------------
# Staff photo upload URL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_staff_photo_upload_url_returns_upload_result():
    repo = make_mock_repo()
    repo.list_owner_staff.return_value = [{"id": "staff-007"}]
    repo.get_owner_salon.return_value = SALON
    gw = _FakeStorageGateway()
    uc = OwnerUseCases(repo, storage_gateway=gw)
    owner = make_owner()

    result = await uc.get_staff_photo_upload_url(
        owner,
        staff_id="staff-007",
        content_type="image/webp",
        filename="photo.webp",
        bucket="salon-images",
    )

    assert "upload_url" in result
    assert "public_url" in result
    assert result["expires_in"] == 300
    # Object key must be scoped to salon + staff
    assert "staff-photos/salon-001/staff-007/" in result["upload_url"]
    assert "staff-photos/salon-001/staff-007/" in result["public_url"]


@pytest.mark.asyncio
async def test_get_staff_photo_upload_url_raises_when_no_gateway():
    """Calling get_staff_photo_upload_url without a gateway is a programming error."""
    repo = make_mock_repo()
    repo.get_owner_salon.return_value = SALON
    uc = OwnerUseCases(repo)  # no storage_gateway — assert guards against this
    owner = make_owner()

    with pytest.raises(AssertionError, match="storage_gateway is required for staff photo upload"):
        await uc.get_staff_photo_upload_url(
            owner, staff_id="staff-007", content_type="image/jpeg", filename="f.jpg", bucket="salon-images"
        )


@pytest.mark.asyncio
async def test_get_staff_photo_upload_url_raises_for_non_owner():
    repo = make_mock_repo()
    gw = _FakeStorageGateway()
    uc = OwnerUseCases(repo, storage_gateway=gw)
    customer = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.get_staff_photo_upload_url(
            customer, staff_id="staff-007", content_type="image/jpeg", filename="f.jpg", bucket="salon-images"
        )
