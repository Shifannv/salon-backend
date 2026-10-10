"""Keyed digests and opaque tokens for account-deletion flows."""

import hashlib
import hmac
import secrets


def new_token() -> str:
    """Return an unguessable URL-safe token (256 bits)."""

    return secrets.token_urlsafe(32)


def digest(secret: str, purpose: str, value: str) -> str:
    """Return a purpose-bound HMAC-SHA256 hex digest; never store the raw value."""

    message = f"{purpose}:{value}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def digests_match(left: str | None, right: str | None) -> bool:
    """Constant-time comparison that treats missing values as a mismatch."""

    if not left or not right:
        return False
    return hmac.compare_digest(left.encode(), right.encode())
