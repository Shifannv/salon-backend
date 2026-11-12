"""Rules for sending a payout through the provider. Pure Python, integer paise.

The provider moves the money; these rules only decide how to ask: which rail fits the amount, the
ids that make a retry safe (a lost reply is looked up, never re-sent), and how the provider's
statuses map to ours.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from decimal import Decimal

# Bank rails have their own ceilings; the provider refuses anything above them.
UPI_LIMIT_PAISE = 1_00_000_00
IMPS_LIMIT_PAISE = 5_00_000_00

MODES = ("upi", "imps")

_FAILED = {"FAILED", "REJECTED", "MANUALLY_REJECTED", "CANCELLED"}


class TransferProblem(ValueError):
    """The payout cannot be sent as asked. The message is safe to show the admin."""


def choose_mode(amount_paise: int, *, has_upi: bool, has_bank: bool) -> str:
    """UPI when the salon saved a UPI id and the amount fits; otherwise IMPS to the bank account."""

    if has_upi and amount_paise <= UPI_LIMIT_PAISE:
        return "upi"
    if has_bank and amount_paise <= IMPS_LIMIT_PAISE:
        return "imps"
    if not has_upi and not has_bank:
        raise TransferProblem("The salon has not saved a bank account or UPI id")
    raise TransferProblem("The amount is above what the saved account can receive in one transfer")


def transfer_id_for(request_id: str, attempt: int) -> str:
    """Our id at the provider: one per request and attempt, within its 40 characters."""

    return f"po_{request_id.replace('-', '')}_{attempt}"


def beneficiary_id_for(salon_id: str, identity: str, secret: str = "") -> str:
    """Content-addressed: the same salon and account always give the same id, a changed account a new one.

    The id is stored in the clear, so it is keyed with a server secret: an unkeyed hash of an account number
    could be guessed offline. Without a secret (local development) it falls back to a plain hash.
    """

    if secret:
        subkey = hashlib.sha256(b"payout-beneficiary-v1|" + secret.encode()).digest()
        digest = hmac.new(subkey, f"{salon_id}|{identity}".encode(), hashlib.sha256).hexdigest()[:20]
    else:
        digest = hashlib.sha256(identity.encode()).hexdigest()[:12]
    return f"sl_{salon_id.replace('-', '')[:16]}_{digest}"


def clean_beneficiary_name(name: str | None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 .\-]", " ", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()[:100]
    return cleaned or "Salon Owner"


def normalize_phone(raw: str | None) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    return digits[-10:] if len(digits) >= 10 else None


def rupees(amount_paise: int) -> Decimal:
    return (Decimal(amount_paise) / 100).quantize(Decimal("0.01"))


def map_status(provider_status: str | None) -> str:
    """Our transfer status from the provider's: success, failed, reversed, or still pending."""

    status = (provider_status or "").strip().upper()
    if status == "SUCCESS":
        return "success"
    if status in _FAILED:
        return "failed"
    if status == "REVERSED":
        return "reversed"
    return "pending"
