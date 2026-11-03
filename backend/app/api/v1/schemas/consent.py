"""Consent request and status shapes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConsentRequest(BaseModel):
    """What a person confirms on the consent screen.

    The three required confirmations must all be true; marketing is a separate choice that is
    off unless the person turns it on.
    """

    model_config = ConfigDict(extra="forbid")

    source: Literal["customer_app", "owner_app", "walkin_web"]
    accept_terms: bool = Field(description="Accepts the current Terms of Service")
    accept_privacy: bool = Field(description="Has read the current Privacy Policy")
    age_13_plus: bool = Field(description="Confirms being 13 years old or older")
    marketing: bool = Field(default=False, description="Optional offers and promotions; off by default")


class ConsentStatusResponse(BaseModel):
    """The versions in force, what this person has accepted, and whether they must accept again."""

    terms_version: str
    privacy_version: str
    accepted_terms_version: str | None = None
    accepted_privacy_version: str | None = None
    age_13_plus: bool = False
    marketing: bool = False
    needs_consent: bool


class MarketingChoiceRequest(BaseModel):
    """Turn offers and news on or off after the first consent screen."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["customer_app", "owner_app", "walkin_web"]
    marketing: bool
