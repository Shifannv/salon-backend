"""Request media fields contain hosted URLs, never inline image payloads."""
from typing import ClassVar
from urllib.parse import urlsplit

from pydantic import BaseModel, model_validator


class HostedMediaRequest(BaseModel):
    avatar_references: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="before")
    @classmethod
    def hosted_media_only(cls, values):
        if not isinstance(values, dict):
            return values
        for name in ("avatar_url", "photo_url", "image_url", "url"):
            value = values.get(name)
            if value is None:
                continue
            if name == "avatar_url" and isinstance(value, str) and value in cls.avatar_references:
                continue
            if not isinstance(value, str) or len(value) > 2048:
                raise ValueError("Image URL must be a hosted HTTP or HTTPS URL")
            try:
                parts = urlsplit(value)
                valid = parts.scheme in {"http", "https"} and parts.hostname and not parts.username and not parts.password
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("Image URL must be a hosted HTTP or HTTPS URL")
        return values
