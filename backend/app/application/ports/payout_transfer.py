"""Payout transfer port: sends a salon's payout to its bank or UPI account through a provider.

Separate from ``PaymentGateway`` (which collects customer money): the two share no methods and
have separate credentials. Amounts are integer paise; converting to the provider's unit is the
adapter's job.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BeneficiaryRequest:
    """The account to pay. Holds the full account number: build it, send it, never log it."""

    beneficiary_id: str
    name: str
    phone: str
    mode: str  # 'upi' | 'imps'
    vpa: str | None = None
    bank_account_number: str | None = None
    ifsc: str | None = None


@dataclass(frozen=True, slots=True)
class TransferRequest:
    transfer_id: str
    beneficiary_id: str
    amount_paise: int
    mode: str
    remarks: str


@dataclass(frozen=True, slots=True)
class TransferResult:
    """What the provider says about one transfer."""

    transfer_id: str
    status: str  # the provider's own status word, upper case
    cf_transfer_id: str | None = None
    status_code: str | None = None
    utr: str | None = None
    description: str | None = None


class PayoutTransferGateway(ABC):
    """Distinct from ``payment_provider.PayoutProvider`` (the booking-payment core): this one pays a salon's payout request."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """The name used in the webhook path: ``POST /webhooks/payouts/{provider_name}``."""

    @abstractmethod
    async def upsert_beneficiary(self, beneficiary: BeneficiaryRequest) -> None:
        """Make sure the account exists at the provider. Already existing is success."""

    @abstractmethod
    async def create_transfer(self, request: TransferRequest) -> TransferResult:
        """Start one transfer. A timeout or 5xx raises ``PayoutOutcomeUnknownError``: look it up, never re-send."""

    @abstractmethod
    async def get_transfer(self, transfer_id: str) -> TransferResult | None:
        """The transfer by our id, or None when the provider has no such transfer."""

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        """Whether the webhook really came from the provider."""

    @abstractmethod
    def parse_webhook(self, raw_body: bytes) -> TransferResult | None:
        """The transfer an event is about, or None for an event this app does not act on."""
