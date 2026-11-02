"""Rules for recording that a payout was paid. Pure Python, integer paise.

A payout is paid with proof: the bank or UPI reference, when and how it was paid, the amount, and a
screenshot or PDF of the transfer. The file type is read from its first bytes, never from the name
or the type the browser claims.
"""

from __future__ import annotations

from datetime import datetime, timedelta

MAX_PROOF_BYTES = 5 * 1024 * 1024
MAX_REFERENCE = 100
MAX_NOTE = 200
MIN_REASON = 3
MAX_REASON = 500
PAYMENT_METHODS = ("upi", "imps", "neft", "rtgs", "other")
# A clock a few minutes ahead on the admin's device is not a future payment.
CLOCK_SKEW = timedelta(minutes=5)

PROOF_TYPES = ("image/png", "image/jpeg", "image/webp", "application/pdf")


class PaymentProblem(ValueError):
    """The payment details are not acceptable. The message is safe to show the admin."""


def detect_proof_type(data: bytes) -> str | None:
    """The real file type from its signature, or None when it is not an allowed proof."""

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def check_proof(data: bytes) -> str:
    """The proof's file type, or why it is refused."""

    if not data:
        raise PaymentProblem("Attach the payment screenshot or PDF")
    if len(data) > MAX_PROOF_BYTES:
        raise PaymentProblem("The proof file is larger than 5 MB")
    kind = detect_proof_type(data)
    if kind is None:
        raise PaymentProblem("The proof must be a PNG, JPG, WebP or PDF file")
    return kind


def clean_reference(value: str) -> str:
    ref = value.strip()
    if not 1 <= len(ref) <= MAX_REFERENCE:
        raise PaymentProblem(f"The payment reference must be 1-{MAX_REFERENCE} characters")
    return ref


def clean_reason(value: str | None, *, required: bool, what: str) -> str | None:
    text = (value or "").strip()
    if not text:
        if required:
            raise PaymentProblem(f"Write why {what}")
        return None
    if not MIN_REASON <= len(text) <= MAX_REASON:
        raise PaymentProblem(f"The reason must be {MIN_REASON}-{MAX_REASON} characters")
    return text


def clean_note(value: str | None) -> str | None:
    text = (value or "").strip()
    if len(text) > MAX_NOTE:
        raise PaymentProblem(f"The note can be at most {MAX_NOTE} characters")
    return text or None


def check_method(value: str) -> str:
    method = value.strip().lower()
    if method not in PAYMENT_METHODS:
        raise PaymentProblem("Choose how it was paid: UPI, IMPS, NEFT, RTGS or other")
    return method


def check_paid_at(paid_at: datetime, *, requested_at: datetime, now: datetime) -> datetime:
    """When it was paid: with a time zone, not in the future, not before the request was made."""

    if paid_at.tzinfo is None:
        raise PaymentProblem("The payment time needs a time zone")
    if paid_at > now + CLOCK_SKEW:
        raise PaymentProblem("The payment time cannot be in the future")
    if paid_at < requested_at:
        raise PaymentProblem("The payment time cannot be before the payout was requested")
    return paid_at


def needs_adjustment_reason(requested_paise: int, paid_paise: int) -> bool:
    return paid_paise != requested_paise
