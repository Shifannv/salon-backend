"""Settings normalization tests."""

from app.core.config import Settings


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
