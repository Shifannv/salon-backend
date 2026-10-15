"""Behavior of helpers extracted from duplicated private copies."""

import hashlib
import hmac
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.domain.value_objects.money import round_money
from app.infrastructure.db.json_utils import decode_json
from app.infrastructure.webhook_signing import header, hex_hmac


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (Decimal("1.005"), Decimal("1.01")),
        ("2.345", Decimal("2.35")),
        (7, Decimal("7.00")),
        (Decimal("-0.005"), Decimal("-0.01")),
    ],
)
def test_round_money_is_half_up_and_coerces(raw, expected):
    assert round_money(raw) == expected


def test_decode_json_handles_text_and_python_values():
    assert decode_json('{"a": [1]}') == {"a": [1]}
    assert decode_json({"a": [1]}) == {"a": [1]}
    assert decode_json(None) is None


def test_header_lookup_is_case_insensitive_and_missing_is_none():
    headers = {"X-Razorpay-Signature": "sig"}
    assert header(headers, "x-razorpay-signature") == "sig"
    assert header(headers, "x-missing") is None


def test_hex_hmac_matches_stdlib():
    expected = hmac.new(b"secret", b"body", hashlib.sha256).hexdigest()
    assert hex_hmac("secret", b"body") == expected


def test_media_bucket_defaults_when_unset():
    assert Settings.model_construct(r2_bucket=None).media_bucket == "salon-images"
    assert Settings.model_construct(r2_bucket="custom").media_bucket == "custom"
