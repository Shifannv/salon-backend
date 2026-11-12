"""Working hours and break schedule schemas used on write paths."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class BreakInterval(BaseModel):
    """A single recurring daily break window."""

    id: str | None = None
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM 24-hour start")
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM 24-hour end")

    @model_validator(mode="after")
    def end_after_start(self) -> "BreakInterval":
        if self.end <= self.start:
            raise ValueError("Break end time must be after break start time")
        return self


class DaySchedule(BaseModel):
    """Operating hours for one day, with optional recurring breaks."""

    open: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    close: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    breaks: list[BreakInterval] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_breaks(self) -> "DaySchedule":
        for b in self.breaks:
            if b.start < self.open or b.end > self.close:
                raise ValueError(
                    f"Break {b.start}–{b.end} must be within operating hours {self.open}–{self.close}"
                )
        sorted_breaks = sorted(self.breaks, key=lambda x: x.start)
        for i in range(len(sorted_breaks) - 1):
            if sorted_breaks[i].end > sorted_breaks[i + 1].start:
                raise ValueError("Breaks cannot overlap each other")
        return self


# Mapping of day-of-week keys to their schedule (None means closed that day).
WorkingHoursMap = dict[
    Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    DaySchedule | None,
]
