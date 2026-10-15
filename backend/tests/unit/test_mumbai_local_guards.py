"""Wrong-region settings must fail before a staging connection can be opened."""

import base64
import json

import pytest

from scripts.mumbai_local import BASE, REF, require, validate


def settings():
    claims = base64.urlsafe_b64encode(json.dumps({"ref": REF, "role": "service_role"}).encode()).decode().rstrip("=")
    return {
        "SUPABASE_URL": BASE,
        "SUPABASE_JWKS_URL": BASE + "/auth/v1/.well-known/jwks.json",
        "DATABASE_URL": f"postgresql+asyncpg://postgres:synthetic@db.{REF}.supabase.co:5432/postgres",
        # Synthetic claim screen only. Live Admin authorization is tested separately.
        "SUPABASE_SERVICE_ROLE_KEY": "synthetic." + claims + ".unsigned",
    }


def test_claim_screen_accepts_the_mumbai_target():
    assert validate(settings()).hostname == f"db.{REF}.supabase.co"


@pytest.mark.parametrize("field,value", [
    ("SUPABASE_URL", "https://different-project.supabase.co"),
    ("SUPABASE_JWKS_URL", "https://different-project.supabase.co/auth/v1/.well-known/jwks.json"),
    ("DATABASE_URL", f"postgresql+asyncpg://postgres.{REF}:synthetic@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres"),
])
def test_wrong_project_or_region_is_rejected_before_connecting(field, value):
    values = settings()
    values[field] = value
    with pytest.raises(ValueError, match="target mismatch"):
        validate(values)


def test_target_guard_does_not_depend_on_python_assertions():
    with pytest.raises(ValueError, match="wrong target"):
        require(False, "wrong target")
