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
    r2_account_id="test-account",
    r2_access_key_id="test-key",
    r2_secret_access_key="test-secret",
    r2_bucket="salon-images",
    r2_public_url="https://pub-test.r2.dev",
)

_PARTIAL_SETTINGS = Settings(
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
async def test_get_upload_url_calls_boto3_with_correct_params():
    gw = R2StorageGateway(_FULL_SETTINGS)

    fake_url = "https://fake-presigned.r2.dev/put?sig=abc"
    fake_client = MagicMock()
    fake_client.generate_presigned_url.return_value = fake_url

    with patch.object(gw, "_build_client", return_value=fake_client):
        url = await gw.get_upload_url("salon-images", "salon-images/s1/img.jpeg", "image/jpeg")

    assert url == fake_url
    fake_client.generate_presigned_url.assert_called_once_with(
        "put_object",
        Params={"Bucket": "salon-images", "Key": "salon-images/s1/img.jpeg", "ContentType": "image/jpeg"},
        ExpiresIn=300,
    )


@pytest.mark.asyncio
async def test_get_upload_url_raises_validation_error_on_boto3_failure():
    gw = R2StorageGateway(_FULL_SETTINGS)

    fake_client = MagicMock()
    fake_client.generate_presigned_url.side_effect = RuntimeError("network error")

    with (
        patch.object(gw, "_build_client", return_value=fake_client),
        pytest.raises(ValidationError, match="Could not generate R2 upload URL"),
    ):
        await gw.get_upload_url("salon-images", "salon-images/s1/img.jpeg", "image/jpeg")


@pytest.mark.asyncio
async def test_get_upload_url_raises_when_r2_not_configured():
    gw = R2StorageGateway(_PARTIAL_SETTINGS)
    with pytest.raises(ValidationError, match="R2_ACCESS_KEY_ID"):
        await gw.get_upload_url("salon-images", "path/to/img.jpeg", "image/jpeg")


# ---------------------------------------------------------------------------
# boto3 client caching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_client_caches_boto3_client_across_calls():
    gw = R2StorageGateway(_FULL_SETTINGS)

    fake_client = MagicMock()
    fake_client.generate_presigned_url.return_value = "https://presigned.example.com"

    with patch.object(gw, "_build_client", return_value=fake_client) as mock_build:
        await gw.get_upload_url("salon-images", "path/img.jpeg", "image/jpeg")
        await gw.get_upload_url("salon-images", "path/img2.jpeg", "image/webp")

    # _build_client should only be called once despite two presign calls
    mock_build.assert_called_once()


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
