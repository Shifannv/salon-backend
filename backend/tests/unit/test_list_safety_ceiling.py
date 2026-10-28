"""List endpoints with no client limit are capped, and paging is always bound."""

from app.infrastructure.db.repositories.platform._sql import LIST_SAFETY_CEILING, page_bounds


def test_no_limit_applies_the_safety_ceiling():
    assert page_bounds(None, 0) == {"limit": LIST_SAFETY_CEILING, "offset": 0}


def test_offset_is_honoured_without_a_limit():
    assert page_bounds(None, 40) == {"limit": LIST_SAFETY_CEILING, "offset": 40}


def test_explicit_limit_is_kept_and_clamped_to_the_ceiling():
    assert page_bounds(25, 0)["limit"] == 25
    assert page_bounds(10_000, 0)["limit"] == LIST_SAFETY_CEILING


def test_negative_offset_never_reaches_sql():
    assert page_bounds(10, -5)["offset"] == 0
