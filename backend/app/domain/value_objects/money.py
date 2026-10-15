"""Money value object."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_ZERO = Decimal("0.00")
_CENT = Decimal("0.01")


def round_money(value: Decimal | int | str) -> Decimal:
    """Quantize to whole paise (two places), ROUND_HALF_UP; the sign is not restricted."""
    return Decimal(value).quantize(_CENT, ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Money:
    """An immutable monetary amount — always Decimal, never float.

    All arithmetic uses ROUND_HALF_UP (standard accounting convention).
    """

    amount: Decimal

    def __post_init__(self) -> None:
        """Coerce and validate amount."""
        # Transparently accept int / str in addition to Decimal.
        object.__setattr__(self, "amount", Decimal(self.amount).quantize(_CENT, ROUND_HALF_UP))
        if self.amount < _ZERO:
            raise ValueError(f"Money amount cannot be negative: {self.amount}")

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.amount - other.amount)

    def __mul__(self, factor: int | Decimal) -> "Money":
        return Money(self.amount * Decimal(factor))

    def __str__(self) -> str:
        return str(self.amount)

    def __repr__(self) -> str:
        return f"Money({self.amount!r})"
