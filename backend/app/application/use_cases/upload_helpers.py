"""Shared helpers for signed-upload use cases."""

from typing import Any

from app.application.ports.storage_gateway import _UPLOAD_TTL_SECONDS
from app.core.exceptions import ValidationError


def _upload_extension(filename: str, content_type: str) -> str:
    allowed = {"image/jpeg": {"jpg", "jpeg"}, "image/png": {"png"}, "image/webp": {"webp"}}
    extension = filename.rsplit(".", 1)[-1].lower()
    if content_type not in allowed or extension not in allowed[content_type]:
        raise ValidationError("Image filename and content type must agree; use JPEG, PNG or WebP")
    return "jpeg" if extension == "jpg" else extension


def _extract_r2_object_key(public_url: str, r2_public_base: str) -> str | None:
    """Extract the R2 object key from a public URL.

    Returns the path component after the R2 public base URL, or ``None`` if
    the URL does not belong to this R2 bucket (e.g. an external avatar URL).

    Args:
        public_url: The full public URL stored in the database.
        r2_public_base: The configured R2_PUBLIC_URL base (e.g. 'https://pub-xxx.r2.dev').

    Returns:
        Object key string (e.g. 'avatars/abc/avatar.jpeg'), or None.
    """
    base = r2_public_base.rstrip("/")
    if public_url.startswith(base + "/"):
        return public_url[len(base) + 1:]
    return None


def _upload_result(upload_url: str, public_url: str, result_url: str | None) -> dict[str, Any]:
    """Return the standard upload URL response payload."""
    return {
        "upload_url": upload_url,
        "public_url": public_url,
        "expires_in": _UPLOAD_TTL_SECONDS,
        "result_url": result_url,
    }
