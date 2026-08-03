"""Shared pagination helpers."""

from pydantic import BaseModel, Field


class LimitOffsetPage(BaseModel):
    """Limit-offset pagination request values."""

    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
