"""Super-admin feature access API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Audience = Literal["trial", "growth", "premium"]
Tier = Literal["growth", "premium"]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FeatureAccessCell(_Request):
    feature_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    audience: Audience
    enabled: bool


class FeatureMatrixRequest(_Request):
    cells: list[FeatureAccessCell] = Field(min_length=1, max_length=90)


class FeatureUpdateRequest(_Request):
    label: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=400)


class FeatureRow(BaseModel):
    key: str
    label: str
    description: str
    sort_order: int
    access: dict[Audience, bool]


class PlanContent(BaseModel):
    headline: str = ""
    description: str = ""
    bullets: list[str] = Field(default_factory=list)


class PlanContentRequest(_Request):
    headline: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=600)
    bullets: list[str] = Field(default_factory=list, max_length=12)


class FeatureOverviewResponse(BaseModel):
    features: list[FeatureRow]
    plan_content: dict[Tier, PlanContent]


class FeatureOverrideRequest(_Request):
    enabled: bool
    expires_at: datetime | None = None
    note: str | None = Field(default=None, max_length=200)


class FeatureOverrideResponse(BaseModel):
    feature_key: str
    enabled: bool
    expires_at: datetime | None = None
    note: str | None = None
    updated_at: datetime
