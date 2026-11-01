"""Contract tests for the rolling customer booking window."""

from pathlib import Path

from app.core.exceptions import BookingWindowExceededError
from app.infrastructure.db.repositories.platform._sql import (
    _CREATE_BOOKING_ERROR_RULES,
    _error_for_message,
)


def test_booking_window_database_error_has_a_stable_api_code() -> None:
    error = _error_for_message(
        "booking_window_exceeded", _CREATE_BOOKING_ERROR_RULES
    )

    assert isinstance(error, BookingWindowExceededError)
    assert error.code == "booking_window_exceeded"
    assert error.status_code == 422


def test_booking_window_sql_uses_salon_local_rolling_dates() -> None:
    sql_path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "sql"
        / "0052_booking_window_30_days.sql"
    )
    sql = sql_path.read_text(encoding="utf-8")

    assert "v_today := (now() at time zone v_tz)::date" in sql
    assert "p_date > v_today + 60" in sql
    assert "v_booking_date > v_today + 60" in sql
    assert "p_source = 'app'" in sql
