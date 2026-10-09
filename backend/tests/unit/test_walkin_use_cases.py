"""Unit tests for WalkIn use cases."""

import pytest

from app.application.use_cases.walkin import WalkInUseCases
from app.core.exceptions import NotFoundError
from tests.conftest import make_mock_repo

WALKIN_SALON = {
    "id": "salon-001",
    "name": "Scissors & Style",
    "description": None,
    "city": "Kozhikode",
    "timezone": "Asia/Kolkata",
    "approval_mode": "auto",
    "services": [],
    "staff": [],
}


@pytest.mark.asyncio
async def test_get_salon_by_qr_delegates():
    repo = make_mock_repo()
    repo.get_salon_by_qr.return_value = WALKIN_SALON
    uc = WalkInUseCases(repo)

    salon = await uc.resolve_qr_token("some-qr-token")
    assert salon["id"] == "salon-001"
    repo.get_salon_by_qr.assert_awaited_once_with("some-qr-token")


@pytest.mark.asyncio
async def test_get_salon_by_qr_not_found():
    repo = make_mock_repo()
    repo.get_salon_by_qr.side_effect = NotFoundError("Salon not found")
    uc = WalkInUseCases(repo)

    with pytest.raises(NotFoundError):
        await uc.resolve_qr_token("invalid-token")


@pytest.mark.asyncio
async def test_booking_context_rejects_owner_before_database_lookup():
    from unittest.mock import AsyncMock

    from app.core.exceptions import ForbiddenError
    from tests.conftest import make_owner

    repo = make_mock_repo()
    repo.validate_qr_token = AsyncMock()
    with pytest.raises(ForbiddenError):
        await WalkInUseCases(repo).validate_booking_context(make_owner(), "qr-a", {})
    repo.validate_qr_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_booking_context_rejects_cross_salon_and_keeps_qr_source():
    from unittest.mock import AsyncMock

    from app.core.exceptions import ValidationError
    from tests.conftest import make_profile

    repo = make_mock_repo()
    repo.validate_qr_token = AsyncMock(return_value="salon-a")
    uc = WalkInUseCases(repo)
    with pytest.raises(ValidationError):
        await uc.create_walkin_booking(make_profile(), "qr-a", {"salon_id": "salon-b"})
    repo.create_booking.assert_not_awaited()
    await uc.create_walkin_booking(make_profile(), "qr-a", {"salon_id": "salon-a", "source": "app"})
    assert repo.create_booking.call_args.args[0]["source"] == "qr_walkin"
