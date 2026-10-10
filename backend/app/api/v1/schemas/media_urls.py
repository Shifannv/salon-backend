"""Request media fields contain hosted URLs, never inline image payloads."""
from urllib.parse import urlsplit

from pydantic import BaseModel, model_validator


class HostedMediaRequest(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def hosted_media_only(cls, values):
        if not isinstance(values, dict):
            return values
        for name in ("avatar_url", "photo_url", "image_url", "url"):
            value = values.get(name)
            if value is None:
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
