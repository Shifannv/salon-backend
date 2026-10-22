"""Provider-neutral finance observations. Mock evidence never verifies a provider.

No tariff, fee bearer, payout schedule, custody model or eligibility decision is
inferred here. Database persistence belongs to the reviewed migration designs.
"""

from dataclasses import dataclass, field, fields
from enum import StrEnum

from app.domain.value_objects.money import Money


class PayoutStatus(StrEnum):
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    reversed = "reversed"


class EvidenceSource(StrEnum):
    unknown = "unknown"
    mock = "mock"


def require_positive_money(amount: Money) -> None:
    if not isinstance(amount, Money) or not amount.amount.is_finite() or amount.amount <= 0:
        raise ValueError("A positive finite Money amount is required")


@dataclass(frozen=True, slots=True)
class ProviderFees:
    """Independent components, in INR. None is unknown; zero needs explicit evidence."""

    gateway_fee: Money | None = None
    gateway_fee_tax: Money | None = None
    easy_split_fee: Money | None = None
    settlement_fee: Money | None = None
    payout_fee: Money | None = None
    refund_fee: Money | None = None

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if value is not None and (
                not isinstance(value, Money)
                or not value.amount.is_finite()
                or value.amount < 0
            ):
                raise ValueError("Fee components must be finite nonnegative Money or None")

    def as_record(self) -> dict[str, str | None]:
        """Lossless decimal-string projection; no total that hides unknown costs."""
        return {
            item.name: str(value.amount) if (value := getattr(self, item.name)) is not None else None
            for item in fields(self)
        }


@dataclass(frozen=True, slots=True)
class PayoutRequest:
    salon_id: str
    destination_reference: str = field(repr=False)
    amount: Money
    idempotency_key: str = field(repr=False)
    currency: str = "INR"

    def __post_init__(self) -> None:
        require_positive_money(self.amount)
        if self.currency != "INR":
            raise ValueError("Only INR is supported")
        if not self.salon_id or not self.destination_reference or not self.idempotency_key:
            raise ValueError("Salon, destination and idempotency references are required")


@dataclass(frozen=True, slots=True)
class ProviderPayout:
    provider: str
    payout_reference: str
    amount: Money
    status: PayoutStatus
    currency: str = "INR"
    provider_transfer_reference: str | None = field(default=None, repr=False)
    provider_settlement_reference: str | None = field(default=None, repr=False)
    evidence_source: EvidenceSource = EvidenceSource.unknown
    provider_verified: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class ProviderFeeReconciliation:
    provider: str
    reference: str = field(repr=False)
    fees: ProviderFees = field(default_factory=ProviderFees)
    currency: str = "INR"
    evidence_source: EvidenceSource = EvidenceSource.unknown
    provider_transfer_reference: str | None = field(default=None, repr=False)
    provider_settlement_reference: str | None = field(default=None, repr=False)
    provider_verified: bool = field(default=False, init=False)
