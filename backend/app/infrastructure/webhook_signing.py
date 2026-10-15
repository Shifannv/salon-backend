"""Header lookup and HMAC helpers shared by payment and subscription provider adapters."""

import hashlib
import hmac
from collections.abc import Mapping


def header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup that also works on a plain dict."""
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return None


def hex_hmac(secret: str, message: bytes) -> str:
    """Hex SHA-256 HMAC of ``message`` keyed by ``secret``."""
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
