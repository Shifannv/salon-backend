"""Unit tests for R2StorageGateway.

boto3 is mocked throughout — no real AWS/R2 calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.infrastructure.r2.storage import R2StorageGateway

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_SETTINGS = Settings(
    _env_file=None,
    r2_account_id="test-account",
    r2_access_key_id="test-key",
    r2_secret_access_key="test-secret",
    r2_bucket="salon-images",
    r2_public_url="https://pub-test.r2.dev",
)

_PARTIAL_SETTINGS = Settings(
    _env_file=None,
    r2_account_id="test-account",
    # r2_access_key_id intentionally missing
    r2_secret_access_key="test-secret",
    r2_bucket="salon-images",
    r2_public_url="https://pub-test.r2.dev",
)


# ---------------------------------------------------------------------------
# _assert_configured
# ---------------------------------------------------------------------------


def test_assert_configured_raises_when_settings_missing():
    gw = R2StorageGateway(_PARTIAL_SETTINGS)
    with pytest.raises(ValidationError, match="R2_ACCESS_KEY_ID"):
        gw._assert_configured()


def test_assert_configured_passes_when_all_settings_present():
    gw = R2StorageGateway(_FULL_SETTINGS)
    gw._assert_configured()  # should not raise


# ---------------------------------------------------------------------------
# get_public_url
# ---------------------------------------------------------------------------


def test_get_public_url_constructs_url_correctly():
    gw = R2StorageGateway(_FULL_SETTINGS)
    url = gw.get_public_url("salon-images", "salon-images/abc/photo.jpeg")
    assert url == "https://pub-test.r2.dev/salon-images/abc/photo.jpeg"


def test_get_public_url_strips_trailing_slash_from_base():
    settings = Settings(
        _env_file=None,
        r2_account_id="acct",
        r2_access_key_id="key",
        r2_secret_access_key="sec",
        r2_bucket="salon-images",
        r2_public_url="https://pub-test.r2.dev/",  # trailing slash
    )
    gw = R2StorageGateway(settings)
    url = gw.get_public_url("salon-images", "avatars/u1/img.png")
    assert url == "https://pub-test.r2.dev/avatars/u1/img.png"
    assert "//" not in url.replace("https://", "")


# ---------------------------------------------------------------------------
# get_upload_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_url_requires_public_api_origin():
    gw = R2StorageGateway(_FULL_SETTINGS.model_copy(update={"public_api_base_url": None}))
    with pytest.raises(ValidationError, match="PUBLIC_API_BASE_URL"):
        await gw.get_upload_url("salon-images", "salon-images/s1/img.jpeg", "image/jpeg")


@pytest.mark.asyncio
async def test_upload_url_is_a_backend_capability_without_r2_presigning():
    from pydantic import HttpUrl, TypeAdapter
    origin = TypeAdapter(HttpUrl).validate_python("https://api.example.test")
    gw = R2StorageGateway(_FULL_SETTINGS.model_copy(update={"public_api_base_url": origin}))
    with patch.object(gw, "_build_client") as build:
        url = await gw.get_upload_url("salon-images", "salon-images/s1/img.jpeg", "image/jpeg")
    assert url.startswith("https://api.example.test/v1/media/uploads/")
    gw.validate_upload_token(url.rsplit("/", 1)[-1], "image/jpeg")
    build.assert_not_called()


@pytest.mark.asyncio
async def test_get_upload_url_raises_when_r2_not_configured():
    gw = R2StorageGateway(_PARTIAL_SETTINGS)
    with pytest.raises(ValidationError, match="R2_ACCESS_KEY_ID"):
        await gw.get_upload_url("salon-images", "avatars/u/img.jpeg", "image/jpeg")


def test_get_client_caches_boto3_client_across_calls():
    gw = R2StorageGateway(_FULL_SETTINGS)
    fake_client = MagicMock()
    with patch.object(gw, "_build_client", return_value=fake_client) as build:
        assert gw._get_client() is fake_client
        assert gw._get_client() is fake_client
    build.assert_called_once()


# ---------------------------------------------------------------------------
# delete_object
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_object_calls_boto3_delete():
    gw = R2StorageGateway(_FULL_SETTINGS)

    fake_client = MagicMock()

    with patch.object(gw, "_build_client", return_value=fake_client):
        await gw.delete_object("salon-images", "salon-images/s1/old.jpeg")

    fake_client.delete_object.assert_called_once_with(Bucket="salon-images", Key="salon-images/s1/old.jpeg")


@pytest.mark.asyncio
async def test_delete_object_raises_validation_error_on_boto3_failure():
    gw = R2StorageGateway(_FULL_SETTINGS)

    fake_client = MagicMock()
    fake_client.delete_object.side_effect = RuntimeError("s3 error")

    with (
        patch.object(gw, "_build_client", return_value=fake_client),
        pytest.raises(ValidationError, match="Could not delete R2 object"),
    ):
        await gw.delete_object("salon-images", "salon-images/s1/img.jpeg")


@pytest.mark.asyncio
async def test_delete_object_raises_when_r2_not_configured():
    gw = R2StorageGateway(_PARTIAL_SETTINGS)
    with pytest.raises(ValidationError, match="R2_ACCESS_KEY_ID"):
        await gw.delete_object("salon-images", "path/img.jpeg")
