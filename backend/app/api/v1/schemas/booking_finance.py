"""Owner schemas deliberately omit all internal allocation and provider-cost fields."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OwnerPayoutStatement(BaseModel):
    booking_id: UUID
    approved_amount: Decimal
    paid_out_amount: Decimal
    status: Literal['not_applicable','under_review','approved','paid']


class AdminFinanceStatement(BaseModel):
    booking_id: UUID
    policy_version: str
    kind: str
    decision_at: datetime
    appointment_start: datetime
    captured_amount: Decimal
    customer_refund_promised: Decimal
    cancellation_penalty: Decimal
    previously_refunded: Decimal
    refund_due: Decimal
    retained_amount: Decimal
    provider_costs: Decimal | None
    platform_share: Decimal | None
    salon_share: Decimal | None
    platform_shortfall: Decimal | None
    funds_held_verified: bool
    requires_reconciliation: bool
    approved_amount: Decimal
    paid_out_amount: Decimal
    version: int


class FinanceCommandRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)
    action: Literal['provider_costs','hold_review','approve','record_payout']
    amount: Decimal = Field(ge=0,max_digits=10,decimal_places=2,allow_inf_nan=False)
    reference: str = Field(pattern=r'^[A-Za-z0-9_:.\-]{1,128}$')
