"""Unit tests for working-hours break schemas."""

import pytest
from pydantic import TypeAdapter, ValidationError

from app.api.v1.schemas.working_hours import BreakInterval, DaySchedule, WorkingHoursMap

_adapter = TypeAdapter(WorkingHoursMap)


def test_break_end_must_follow_start():
    with pytest.raises(ValidationError):
        BreakInterval(start="14:00", end="13:00")
    with pytest.raises(ValidationError):
        BreakInterval(start="13:00", end="13:00")


def test_break_must_use_hh_mm():
    with pytest.raises(ValidationError):
        BreakInterval(start="1pm", end="2pm")


def test_breaks_must_sit_inside_operating_hours():
    with pytest.raises(ValidationError):
        DaySchedule(open="09:00", close="18:00", breaks=[{"start": "08:30", "end": "09:30"}])
    with pytest.raises(ValidationError):
        DaySchedule(open="09:00", close="18:00", breaks=[{"start": "17:30", "end": "18:30"}])


def test_breaks_cannot_overlap():
    with pytest.raises(ValidationError):
        DaySchedule(
            open="09:00",
            close="20:00",
            breaks=[{"start": "13:00", "end": "14:00"}, {"start": "13:30", "end": "14:30"}],
        )


def test_adjacent_breaks_are_allowed():
    day = DaySchedule(
        open="09:00",
        close="20:00",
        breaks=[{"start": "13:00", "end": "14:00"}, {"start": "14:00", "end": "14:30"}],
    )
    assert len(day.breaks) == 2


def test_legacy_payload_without_breaks_is_accepted():
    parsed = _adapter.validate_python({"mon": {"open": "09:00", "close": "21:00"}, "sun": None})
    assert parsed["mon"].breaks == []
    assert parsed["sun"] is None


def test_unknown_day_key_is_rejected():
    with pytest.raises(ValidationError):
        _adapter.validate_python({"funday": {"open": "09:00", "close": "21:00"}})
