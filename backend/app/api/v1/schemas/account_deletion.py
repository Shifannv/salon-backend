"""Account deletion request/response contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DeletionStatus = Literal["pending", "processing", "completed", "failed"]


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
    requested_at: datetime
    completed_at: datetime | None = None


class AdminAccountDeletionResponse(BaseModel):
    """Ledger row: deliberately carries no name, email, phone or user id."""

    id: UUID
    role: Literal["customer", "owner"]
    salon_id: UUID | None = None
    salon_name: str | None = None
    salon_city: str | None = None
    status: DeletionStatus
    requested_at: datetime
    completed_at: datetime | None = None
