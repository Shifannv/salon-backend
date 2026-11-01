"""Fail-closed GitHub OIDC claim preflight tests."""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "backend" / "scripts" / "wif_claim_preflight.py"


@pytest.fixture
def preflight():
    spec = importlib.util.spec_from_file_location("wif_claim_preflight_test", PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def token(claims: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "header." + payload + ".signature"


def test_exact_approved_claims_pass(preflight, capsys):
    assert preflight.verify(dict(preflight.EXPECTED)) == preflight.EXPECTED
    output = capsys.readouterr().out
    assert "WIF claim preflight: PASS" in output
    assert "signature" not in output


@pytest.mark.parametrize("key", ["sub", "workflow_ref", "actor_id", "event_name", "ref"])
def test_changed_trust_claim_fails_closed(preflight, key, capsys):
    claims = dict(preflight.EXPECTED)
    claims[key] = "unexpected"
    with pytest.raises(RuntimeError, match=f"mismatch: {key}"):
        preflight.verify(claims)
    assert "unexpected" in capsys.readouterr().out


def test_jwt_decoder_never_logs_token(preflight, capsys):
    assert preflight.decode_claims(token(dict(preflight.EXPECTED))) == preflight.EXPECTED
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("value", ["", "not-a-jwt", "a.invalid-json.c"])
def test_invalid_token_fails_closed(preflight, value):
    with pytest.raises(RuntimeError):
        preflight.decode_claims(value)
