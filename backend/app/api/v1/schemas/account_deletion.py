"""Account deletion request/response contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DeletionStatus = Literal["pending", "processing", "completed", "failed"]
DeletionStage = Literal["queued", "refunding", "waiting_for_refunds", "erasing", "completed"]


class StartDeletionChallengeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    channel: Literal["email", "phone"]
    contact: str | None = Field(
        default=None,
        min_length=3,
        max_length=254,
        description="Optional. If sent it must equal the account's verified contact; "
        "the code is only ever delivered to the account's own verified contact.",
    )


class DeletionChallengeResponse(BaseModel):
    challenge_id: UUID
    channel: Literal["email", "phone"]
    masked_destination: str
    expires_at: datetime
    resend_available_at: datetime
    bookings_to_cancel: int = Field(
        default=0,
        description="Owners only: upcoming pending/confirmed bookings that confirming will "
        "cancel (customers are notified and online payments refunded). Always 0 for customers.",
    )


class VerifyDeletionChallengeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(min_length=4, max_length=12, pattern=r"^[0-9A-Za-z]+$")


class VerifiedDeletionChallengeResponse(BaseModel):
    confirmation_token: str
    expires_at: datetime


class ConfirmAccountDeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: UUID
    confirmation_token: str = Field(min_length=20, max_length=128)
    confirm: Literal["DELETE"] = Field(description='Must be exactly "DELETE".')


class AccountDeletionAcceptedResponse(BaseModel):
    request_id: UUID
    status: DeletionStatus
    status_token: str = Field(
        description="Send as the X-Status-Token header to GET /v1/account/deletion/{request_id}. "
        "The JWT stops working as soon as deletion is confirmed."
    )


class AccountDeletionStatusResponse(BaseModel):
    request_id: UUID
    status: DeletionStatus
    stage: DeletionStage = Field(
        description="queued -> (owners) refunding -> waiting_for_refunds -> erasing -> completed. "
        "While refunds settle, status stays pending and stage is waiting_for_refunds."
    )
    requested_at: datetime
    completed_at: datetime | None = None


class AdminAccountDeletionResponse(BaseModel):
    """Ledger row: no name, email, phone or user id. ``salon_name``/``salon_city`` hold the
    live business snapshot only until completion, then the anonymised shell values."""

    id: UUID
    role: Literal["customer", "owner"]
    salon_id: UUID | None = None
    salon_name: str | None = None
    salon_city: str | None = None
    status: DeletionStatus
    requested_at: datetime
    completed_at: datetime | None = None
    attempts: int = 0
    last_error_code: str | None = Field(
        default=None,
        description="Exception class of the last failed step, or refunds_pending while "
        "waiting for refunds. Null when completed.",
    )
    next_attempt_at: datetime | None = None
    updated_at: datetime | None = None


class ClosedSalonFigures(BaseModel):
    """Money totals only: no booking, customer, staff or payment-level detail."""

    currency: str
    online_collected: Decimal = Field(description="Online payments settled, excluding overcollection.")
    online_refunded: Decimal
    platform_fees: Decimal = Field(description="Platform commission charged on online payments.")
    commission_reversed: Decimal = Field(description="Commission returned on refunds.")
    platform_commission_net: Decimal
    overcollected: Decimal
    online_net: Decimal = Field(description="Salon's online net: collected - refunded - net commission.")
    manual_recorded: Decimal = Field(description="Cash/UPI the salon recorded itself.")
    subscription_paid: Decimal = Field(description="Subscription fees the salon paid the platform.")
    subscription_refunded: Decimal = Field(
        description="Attributed to the month the subscription fee was PAID (the billing record has no refund date)."
    )
    platform_revenue: Decimal = Field(description="Net commission + subscription paid - refunded.")
    online_count: int
    manual_count: int


class ClosedSalonMonth(ClosedSalonFigures):
    month: str = Field(pattern=r"^\d{4}-\d{2}$", description="Calendar month in Asia/Kolkata.")


class ClosedSalonStatementResponse(BaseModel):
    """Month-end statement of a salon closed by its owner's account deletion."""

    salon_id: UUID
    months: list[ClosedSalonMonth]
    totals: list[ClosedSalonFigures] = Field(description="One row per currency.")
