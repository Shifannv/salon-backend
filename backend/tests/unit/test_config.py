"""Settings normalization tests."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("secret", ["", "   "])
def test_blank_account_deletion_secret_is_unconfigured(monkeypatch, secret) -> None:
    monkeypatch.setenv("ACCOUNT_DELETION_SECRET", secret)
    settings = Settings(_env_file=None, environment="test")

    assert settings.account_deletion_secret is None


def test_short_account_deletion_secret_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(_env_file=None, environment="test", account_deletion_secret="too-short")


def test_settings_accept_legacy_r2_bucket_name() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        r2_bucket_name="legacy-bucket",
    )

    assert settings.r2_bucket == "legacy-bucket"


def test_settings_derives_r2_account_id_from_legacy_endpoint_url() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        r2_endpoint_url="https://abc123.r2.cloudflarestorage.com",
    )

    assert settings.r2_account_id == "abc123"


def test_explicit_r2_values_win_over_legacy_values() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        r2_account_id="new-account",
        r2_endpoint_url="https://legacy-account.r2.cloudflarestorage.com",
        r2_bucket="new-bucket",
        r2_bucket_name="legacy-bucket",
    )

    assert settings.r2_account_id == "new-account"
    assert settings.r2_bucket == "new-bucket"
