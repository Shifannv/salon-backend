"""Payout proof API schemas (super admin). Money is integer paise."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.v1.schemas.wallet import AdminPayoutAccount, WalletEntryResponse

PaymentMethod = Literal["upi", "imps", "neft", "rtgs", "other"]
PROOF_FORM_DESCRIPTION = "Screenshot or PDF of the transfer: PNG, JPG, WebP or PDF, at most 5 MB."


class PayoutPaymentResponse(BaseModel):
    reference: str
    method: PaymentMethod
    paid_at: datetime
    amount_paid_paise: int
    adjustment_reason: str | None
    note: str | None
    #: Absent for a payout the provider sent: the transfer record is the evidence.
    proof_mime: str | None = None
    proof_size: int | None = None
    source: Literal["manual", "transfer"] = "manual"


class PayoutCorrectionResponse(BaseModel):
    id: str
    delta_paise: int
    reason: str
    reference: str
    created_at: datetime


class PayoutTimelineItem(BaseModel):
    action: Literal[
        "reveal", "pay", "decline", "correct", "view_proof",
        "send_transfer", "transfer_success", "transfer_failed", "transfer_reversed", "transfer_conflict",
    ]
    created_at: datetime
    actor_name: str | None


class BalanceAtRequest(BaseModel):
    """What the platform held for the salon when it asked, so the commission shown is the one then."""

    collected_paise: int
    commission_paise: int
    refunded_paise: int
    commission_reversed_paise: int
    available_paise: int


class PayoutTransferResponse(BaseModel):
    """One provider transfer for a payout. ``pending`` money may already be on its way."""

    transfer_id: str
    mode: Literal["upi", "imps"]
    amount_paise: int
    status: Literal["pending", "success", "failed", "reversed"]
    provider_status: str | None
    utr: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class PayoutDetailResponse(WalletEntryResponse):
    salon_id: str
    salon_name: str | None
    owner_name: str | None
    processed_at: datetime | None
    payout_account: AdminPayoutAccount
    balance_at_request: BalanceAtRequest | None
    payment: PayoutPaymentResponse | None
    transfer: PayoutTransferResponse | None = None
    transfers: list[PayoutTransferResponse] = Field(default_factory=list)
    corrections: list[PayoutCorrectionResponse]
    timeline: list[PayoutTimelineItem]


class ReconciliationDay(BaseModel):
    date: date
    requested_count: int
    requested_paise: int
    paid_count: int
    paid_paise: int
    paid_asked_paise: int
    declined_count: int
    declined_paise: int
    difference_paise: int


class ReconciliationTotals(BaseModel):
    requested_count: int
    requested_paise: int
    paid_count: int
    paid_paise: int
    paid_asked_paise: int
    declined_count: int
    declined_paise: int
    difference_paise: int


class ReconciliationResponse(BaseModel):
    items: list[ReconciliationDay]
    totals: ReconciliationTotals
