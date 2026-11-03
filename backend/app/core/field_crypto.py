"""Application-level encryption for the few database fields that are bank details.

The key lives in the environment, never in the database, so a copy of the database alone does
not reveal an account number. A stored value looks like ``enc:v1:<token>``. The token also
carries the owner row it belongs to (the salon id), so a ciphertext copied onto another row
fails to open. A value without the prefix is a legacy plaintext one and is returned as is until
the backfill script has encrypted it.

``PAYOUT_ENCRYPTION_KEY`` holds one or more Fernet keys separated by commas. The first key
encrypts; every key can decrypt, which is how a key is rotated.
"""

from __future__ import annotations

from app.core.config import settings

PREFIX = "enc:v1:"


class FieldDecryptionError(RuntimeError):
    """A stored value could not be opened with the configured key."""


def _cipher():
    """The configured ``MultiFernet`` or None. Imported on first use to keep API start-up light."""

    from cryptography.fernet import Fernet, MultiFernet

    raw = settings.payout_encryption_key
    if raw is None:
        return None
    keys = [part.strip() for part in raw.get_secret_value().split(",") if part.strip()]
    if not keys:
        return None
    return MultiFernet([Fernet(key.encode()) for key in keys])


def encryption_enabled() -> bool:
    """Whether new values are written encrypted."""

    return _cipher() is not None


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def encrypt_field(value: str | None, binding: str) -> str | None:
    """Encrypt ``value`` for the row ``binding``; return it unchanged when no key is configured."""

    if value is None:
        return None
    cipher = _cipher()
    if cipher is None:
        return value
    token = cipher.encrypt(f"{binding}|{value}".encode()).decode()
    return PREFIX + token


def decrypt_field(value: str | None, binding: str) -> str | None:
    """Return the plain value; legacy plaintext passes through untouched."""

    if value is None or not is_encrypted(value):
        return value
    cipher = _cipher()
    if cipher is None:
        raise FieldDecryptionError("Encrypted value found but PAYOUT_ENCRYPTION_KEY is not set")
    from cryptography.fernet import InvalidToken

    try:
        plain = cipher.decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        raise FieldDecryptionError("Encrypted value could not be opened with the configured key") from None
    owner, _, secret = plain.partition("|")
    if owner != binding:
        raise FieldDecryptionError("Encrypted value belongs to a different record")
    return secret
