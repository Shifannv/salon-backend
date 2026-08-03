from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(APIModel):
    message: str


class Slot(APIModel):
    slot_start: datetime
    slot_end: datetime


class MoneyMixin(APIModel):
    total_price: Decimal = Field(max_digits=10, decimal_places=2)

