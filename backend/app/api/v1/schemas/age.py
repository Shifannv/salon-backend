"""Date of birth and guardian approval request and response shapes."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BirthDateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    birth_date: date = Field(description="Date of birth. It can be set once; later changes need support.")


class GuardianRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guardian_phone: str = Field(
        pattern=r"^\+[1-9][0-9]{7,14}$",
        description="The parent or guardian's mobile number in E.164 form, e.g. +919876543210",
    )


class GuardianVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=r"^[0-9]{6}$", description="The 6-digit code sent to the guardian")


class AgeStatusResponse(BaseModel):
    """Whether this person may book and, if not, the one thing that unlocks it."""

    age_band: Literal["unknown", "child", "teen", "adult"]
    booking_allowed: bool
    block_reason: Literal["birth_date_required", "under_minimum_age", "guardian_consent_required"] | None = None
    guardian_state: Literal["none", "pending", "approved"] = "none"
    guardian_phone_last4: str | None = None
    guardian_code_available: bool = Field(
        default=True, description="False while no SMS provider is connected, so the app can say so."
    )
