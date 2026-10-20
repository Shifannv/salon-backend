"""Additive media responses: existing single URLs remain usable."""

from pydantic import BaseModel, Field


class ImageVariantResponse(BaseModel):
    variant: str
    url: str
    width: int
    height: int
    mime: str
    size: int
    sha256: str


class ImageFamilyResponse(BaseModel):
    public_url: str
    family_id: str
    policy_version: str
    variants: dict[str, ImageVariantResponse]


class AvatarResponse(BaseModel):
    avatar_url: str
    family_id: str | None = None
    policy_version: str | None = None
    variants: dict[str, ImageVariantResponse] = Field(default_factory=dict)
