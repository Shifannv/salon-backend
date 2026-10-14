"""Support HTTP contract; never expose recipients or provider payloads."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    salon_id: UUID | None = None


class SupportReplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    body: str = Field(min_length=1, max_length=5000)


class SupportMessageResponse(BaseModel):
    id: UUID
    author_id: UUID | None
    body: str
    created_at: datetime


class SupportTicketResponse(BaseModel):
    id: UUID
    customer_id: UUID
    salon_id: UUID | None
    subject: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[SupportMessageResponse] = Field(default_factory=list)


class EmailEventResponse(BaseModel):
    id: UUID
    event_type: str
    status: str
    created_at: datetime
    sent_at: datetime | None
