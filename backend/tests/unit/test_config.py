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


def test_messaging_is_off_by_default() -> None:
    settings = Settings(_env_file=None, environment="test")

    assert settings.messaging_provider == "none"
    assert settings.customer_completion_message_enabled is False
    assert settings.messaging_monthly_cap == 300


def test_completion_messages_cannot_be_enabled_without_a_provider() -> None:
    with pytest.raises(ValidationError, match="requires a MESSAGING_PROVIDER"):
        Settings(_env_file=None, environment="test", customer_completion_message_enabled=True)


def test_only_the_fake_messaging_provider_exists_and_only_in_local_or_test() -> None:
    with pytest.raises(ValidationError, match="no adapter"):
        Settings(_env_file=None, environment="test", messaging_provider="twilio")
    with pytest.raises(ValidationError, match="MESSAGING_FAKE_ENABLED"):
        Settings(_env_file=None, environment="test", messaging_provider="fake")
    with pytest.raises(ValidationError, match="local/test"):
        Settings(
            _env_file=None, environment="staging", messaging_provider="fake", messaging_fake_enabled=True
        )
    ok = Settings(
        _env_file=None, environment="test", messaging_provider="fake", messaging_fake_enabled=True,
        customer_completion_message_enabled=True,
    )
    assert ok.messaging_provider == "fake"
