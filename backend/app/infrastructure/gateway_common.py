"""Pure helpers shared by the payment and subscription adapters of one gateway family.

The adapters keep their own ``_request`` (different error mapping); everything that is
byte-for-byte the same lives here. Provider-specific names are passed in by the adapters.
"""

import hmac
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.domain.value_objects.money import Money
from app.infrastructure.webhook_signing import header, hex_hmac


def to_paise(amount: Money) -> int:
    """Convert major units to integer paise."""

    return int((amount.amount * 100).to_integral_value(ROUND_HALF_UP))


def from_paise(paise: int | str | Decimal) -> Money:
    """Convert integer paise to ``Money``."""

    return Money((Decimal(paise) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP))


def verify_webhook_signature(
    secret: str | None, raw_body: bytes, headers: Mapping[str, str], signature_header: str
) -> bool:
    """Check the signature header (HMAC-SHA256 of the raw body) in constant time."""

    signature = header(headers, signature_header)
    if not signature or not secret:
        return False
    return hmac.compare_digest(hex_hmac(secret, raw_body), signature)


def verify_order_payment_signature(
    key_secret: str, order_ref: str, payment_ref: str, signature: str | None
) -> bool:
    """Check the checkout callback signature: HMAC-SHA256 of ``order|payment``."""

    expected = hex_hmac(key_secret, f"{order_ref}|{payment_ref}".encode())
    return hmac.compare_digest(expected, signature or "")


def error_code_of(response: Any) -> str | None:
    """Provider error code from a failed response, or ``None`` when the body has none.

    A non-JSON error body (gateway HTML page, empty body) is ignored on purpose: the
    caller already raises from the HTTP status, and the code is only extra detail.
    """

    try:
        return (response.json().get("error") or {}).get("code")
    except ValueError:
        return None
