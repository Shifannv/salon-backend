"""Idempotency-key helpers shared by use cases."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app.core.exceptions import IdempotencyKeyRequiredError

MIN_KEY_LENGTH = 8


def require_idempotency_key(key: str | None, *, max_len: int) -> str:
    """Return the stripped key, or raise when it is missing or outside 8..max_len."""

    if not key or not key.strip():
        raise IdempotencyKeyRequiredError("The Idempotency-Key header is required")
    key = key.strip()
    if not MIN_KEY_LENGTH <= len(key) <= max_len:
        raise IdempotencyKeyRequiredError(f"Idempotency-Key must be 8-{max_len} characters")
    return key


def check_idempotency_key_length(
    key: str | None, *, max_len: int, reject_blank: bool = True
) -> None:
    """Validate the key as sent (no stripping); the caller keeps using the original value."""

    blank = reject_blank and key is not None and not key.strip()
    if not key or not MIN_KEY_LENGTH <= len(key) <= max_len or blank:
        raise IdempotencyKeyRequiredError(f"Idempotency-Key must be 8-{max_len} characters")


def fingerprint_of(fields: Mapping[str, Any]) -> str:
    """Stable SHA-256 of the request fields, used to detect key reuse with a different body."""

    return hashlib.sha256(json.dumps(fields, sort_keys=True, default=str).encode()).hexdigest()


async def release_reservation(repository: Any, actor_id: str, scope: str, key: str) -> None:
    """Release the idempotency reservation so the client can retry with the same key."""

    await repository.release_idempotent(actor_id, scope, key)
    await repository.commit()
