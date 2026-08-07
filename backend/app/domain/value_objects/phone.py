"""PhoneNumber value object."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Minimal format: optional '+', then 7–15 digits (no spaces/dashes stored).
_DIGITS_RE = re.compile(r"^\+?\d{7,15}$")


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    """Optional phone number.

    Format-only validation: ensures the stored string looks like a phone
    number. Never used as a booking precondition — pass ``None`` freely.
    """

    value: str | None

    def __post_init__(self) -> None:
        """Accept None or a plausible digit string."""
        if self.value is not None and not _DIGITS_RE.match(self.value):
            raise ValueError(f"Invalid phone number format: {self.value!r}")

    def is_present(self) -> bool:
        """Return True when a number was provided."""
        return self.value is not None

    def __str__(self) -> str:
        return self.value or ""

    @classmethod
    def optional(cls, raw: str | None) -> PhoneNumber:
        """Construct from any nullable raw string — never raises on None."""
        return cls(raw)
