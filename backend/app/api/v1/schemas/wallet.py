"""Owner wallet and admin payout API schemas. Money is integer paise; unknown request fields are refused."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.domain.services.wallet import MAX_PAYOUT_PAISE

EntryKind = Literal["earning", "refund", "payout"]
EntryStatus = Literal["completed", "requested", "paid", "rejected", "cancelled"]
PayoutStatus = Literal["requested", "paid", "rejected", "cancelled"]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PayoutRequestCreate(_Request):
    amount_paise: StrictInt = Field(gt=0, le=MAX_PAYOUT_PAISE)
    scheduled_for: date


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
    #: A provider transfer is on its way: the request cannot be cancelled or declined now.
    processing: bool = False
    created_at: datetime
    paid_at: datetime | None = None
    method: Literal["upi", "imps", "neft", "rtgs", "other"] | None = None


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


class AdminPayoutAccountFull(BaseModel):
    """Unmasked, for the super admin who pays one waiting request. Never cached or logged."""

    account_holder_name: str | None
    upi_id: str | None
    bank_name: str | None
    bank_account_number: str | None
    ifsc: str | None
    #: True when the owner changed the account after asking for this payout.
    changed_since_request: bool


class AdminPayoutRequestResponse(WalletEntryResponse):
    salon_id: str
    salon_name: str | None
    amount_paid_paise: int | None = None
    proof_attached: bool = False
    payout_account: AdminPayoutAccount


class AdminPayoutRequestsResponse(BaseModel):
    items: list[AdminPayoutRequestResponse]
    next_cursor: str | None
