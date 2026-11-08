"""Age rules: who may book, from a date of birth and a guardian's approval. Pure functions."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

MINIMUM_AGE = 13
ADULT_AGE = 18
MAX_PLAUSIBLE_AGE = 120

AgeBand = Literal["unknown", "child", "teen", "adult"]
BlockReason = Literal["birth_date_required", "under_minimum_age", "guardian_consent_required"]


def age_on(birth_date: date, today: date) -> int:
    """Whole years completed on ``today``."""

    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def age_band(birth_date: date | None, today: date) -> AgeBand:
    if birth_date is None:
        return "unknown"
    age = age_on(birth_date, today)
    if age < MINIMUM_AGE:
        return "child"
    return "teen" if age < ADULT_AGE else "adult"


def is_plausible_birth_date(birth_date: date, today: date) -> bool:
    return birth_date <= today and age_on(birth_date, today) <= MAX_PLAUSIBLE_AGE


@dataclass(frozen=True, slots=True)
class BookingAccess:
    allowed: bool
    band: AgeBand
    reason: BlockReason | None = None


def booking_access(birth_date: date | None, guardian_approved: bool, today: date) -> BookingAccess:
    """Adults book. Teenagers book once a guardian has approved. Everyone else is blocked."""

    band = age_band(birth_date, today)
    if band == "adult":
        return BookingAccess(True, band)
    if band == "unknown":
        return BookingAccess(False, band, "birth_date_required")
    if band == "child":
        return BookingAccess(False, band, "under_minimum_age")
    if guardian_approved:
        return BookingAccess(True, band)
    return BookingAccess(False, band, "guardian_consent_required")
