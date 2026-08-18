"""TimeSlot value object."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TimeSlot:
    """An immutable half-open time interval [start, end)."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        """Enforce that end is strictly after start."""
        if self.end <= self.start:
            raise ValueError(f"Slot end {self.end!r} must be after start {self.start!r}")

    @property
    def duration_minutes(self) -> int:
        """Duration in whole minutes."""
        return int((self.end - self.start).total_seconds() // 60)

    def overlaps(self, other: "TimeSlot") -> bool:
        """Return True if this slot overlaps with another."""
        return self.start < other.end and other.start < self.end
