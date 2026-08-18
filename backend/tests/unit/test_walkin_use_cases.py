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
