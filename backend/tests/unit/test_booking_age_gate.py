"""POST /bookings asks the age check first, only for app bookings and only while the gate is on."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.routes import bookings
from app.api.v1.schemas.booking import BookingCreateRequest
from app.core.exceptions import GuardianConsentRequiredError
from tests.conftest import make_profile


def payload(**over) -> BookingCreateRequest:
    base = {
        "salon_id": str(uuid4()), "staff_id": str(uuid4()), "service_ids": [str(uuid4())],
        "start_datetime": "2026-11-09T10:00:00+05:30", "customer_name": "Asha",
    }
    return BookingCreateRequest(**{**base, **over})


@pytest.fixture
def wiring():
    gate = MagicMock()
    gate.assert_can_book = AsyncMock()
    create = AsyncMock(side_effect=RuntimeError("stop after the gate"))
    with patch.object(bookings, "guardian_use_cases", return_value=gate), \
         patch.object(bookings, "_use_cases", return_value=MagicMock(create_booking=create)), \
         patch.object(bookings.settings, "age_gate_enforced", True):
        yield gate, create


async def call(body):
    return await bookings.create_booking(body, MagicMock(), make_profile(), AsyncMock(), AsyncMock(), None)


async def test_an_app_booking_is_checked_before_anything_is_created(wiring):
    gate, create = wiring
    gate.assert_can_book.side_effect = GuardianConsentRequiredError("locked")
    with pytest.raises(GuardianConsentRequiredError):
        await call(payload())
    create.assert_not_awaited()


async def test_an_allowed_person_goes_on_to_create_the_booking(wiring):
    gate, create = wiring
    with pytest.raises(RuntimeError, match="stop after the gate"):
        await call(payload())
    gate.assert_can_book.assert_awaited_once()
    create.assert_awaited_once()


async def test_the_gate_does_not_apply_to_salon_side_bookings(wiring):
    gate, _ = wiring
    with pytest.raises(RuntimeError):
        await call(payload(source="manual_walkin"))
    gate.assert_can_book.assert_not_awaited()


async def test_switching_the_gate_off_skips_the_check(wiring):
    gate, _ = wiring
    with patch.object(bookings.settings, "age_gate_enforced", False), pytest.raises(RuntimeError):
        await call(payload())
    gate.assert_can_book.assert_not_awaited()
