"""Owner wallet and admin payout API schemas. Money is integer paise; unknown request fields are refused."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from app.domain.services.wallet import MAX_PAYOUT_PAISE

EntryKind = Literal["earning", "refund", "payout"]
EntryStatus = Literal["completed", "requested", "paid", "rejected", "cancelled"]
PayoutStatus = Literal["requested", "paid", "rejected", "cancelled"]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PayoutRequestCreate(_Request):
    amount_paise: StrictInt = Field(gt=0, le=MAX_PAYOUT_PAISE)
    scheduled_for: date


class PayoutMarkPaidRequest(_Request):
    reference: str = Field(min_length=1, max_length=100)

    @field_validator("reference")
    @classmethod
    def reference_has_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reference must contain a visible character")
        return value


class PayoutRejectRequest(_Request):
    reason: str = Field(min_length=3, max_length=500)


class WalletResponse(BaseModel):
    available_paise: int
    requested_paise: int
    paid_out_paise: int
    min_payout_paise: int
    online_payments_live: bool
    payout_account_ready: bool
    can_request: bool


class WalletEntryResponse(BaseModel):
    id: str
    kind: EntryKind
    direction: Literal["credit", "debit"]
    amount_paise: int
    status: EntryStatus
    reference: str | None
    reject_reason: str | None
    scheduled_for: date | None
    can_cancel: bool
    created_at: datetime


class WalletEntriesResponse(BaseModel):
    items: list[WalletEntryResponse]
    next_cursor: str | None


class AdminPayoutAccount(BaseModel):
    """Masked: the full account number never leaves the database."""

    account_holder_name: str | None
    upi_id: str | None
    bank_name: str | None
    bank_account_last4: str | None
    ifsc: str | None


class AdminPayoutRequestResponse(WalletEntryResponse):
    salon_id: str
    salon_name: str | None
    payout_account: AdminPayoutAccount


class AdminPayoutRequestsResponse(BaseModel):
    items: list[AdminPayoutRequestResponse]
    next_cursor: str | None
