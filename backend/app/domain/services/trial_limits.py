"""Per-salon trial allowances; changing them never resets usage."""

from dataclasses import dataclass

DEFAULT_TRIAL_DAYS = 60
MAX_TRIAL_DAYS = 3650
MAX_TRIAL_BOOKINGS = 1_000_000


@dataclass(frozen=True, slots=True)
class TrialLimits:
    days: int
    # No platform default: the super admin chooses each salon's booking limit when approving it.
    bookings: int

    def __post_init__(self) -> None:
        if type(self.days) is not int or not 1 <= self.days <= MAX_TRIAL_DAYS:
            raise ValueError(f"Trial days must be between 1 and {MAX_TRIAL_DAYS}")
        if type(self.bookings) is not int or not 1 <= self.bookings <= MAX_TRIAL_BOOKINGS:
            raise ValueError(f"Trial booking limit must be between 1 and {MAX_TRIAL_BOOKINGS}")
