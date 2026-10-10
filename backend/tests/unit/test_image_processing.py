"""Real decoder/encoder tests; R2 and Redis never receive original image data."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_storage_gateway
from app.api.v1.routes.media import router
from app.application.ports.image_processor import ImagePolicy
from app.application.use_cases.media import UploadAvatar
from app.core.config import Settings
from app.core.exceptions import ValidationError, register_exception_handlers
from app.infrastructure.media.pillow_processor import PillowImageProcessor
from app.infrastructure.r2.storage import R2StorageGateway
from tests.conftest import make_profile


def photo(size=(3840, 2160), fmt="JPEG", orientation=None, alpha=False):
    image = Image.new("RGBA" if alpha else "RGB", size, (70, 120, 190, 80) if alpha else (70, 120, 190))
    output = BytesIO()
    options = {}
    if orientation:
        exif = Image.Exif()
        exif[274] = orientation
        exif[270] = "Private camera description"
        options["exif"] = exif
    image.save(output, fmt, **options)
    return output.getvalue()


@pytest.mark.parametrize("edge,cap", [(512, 512000), (1024, 1048576), (1600, 1048576)])
def test_real_4k_jpeg_processing(edge, cap):
    original = photo()
    processed = PillowImageProcessor().process(original, "image/jpeg", ImagePolicy(edge, cap))
    with Image.open(BytesIO(processed)) as image:
        assert max(image.size) == edge
        assert abs(image.width / image.height - 3840 / 2160) < 0.01
        assert not image.getexif()
    assert len(processed) < len(original)
    assert len(processed) <= cap


def test_large_png_preserves_transparency():
    processed = PillowImageProcessor().process(photo(fmt="PNG", alpha=True), "image/png", ImagePolicy(1600, 1048576))
    with Image.open(BytesIO(processed)) as image:
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 80
        assert image.size == (1600, 900)


def test_exif_portrait_and_metadata_removed():
    processed = PillowImageProcessor().process(photo(orientation=6), "image/jpeg", ImagePolicy(512, 512000))
    with Image.open(BytesIO(processed)) as image:
        assert image.size == (288, 512)
        assert not image.getexif()


def test_small_image_not_upscaled():
    processed = PillowImageProcessor().process(photo((80, 40)), "image/jpeg", ImagePolicy(512, 512000))
    with Image.open(BytesIO(processed)) as image:
        assert image.size == (80, 40)


def test_bounded_retry_rejects_when_no_output_can_meet_limit():
    with patch.object(Image.Image, "save", wraps=None, side_effect=lambda output, **kw: output.write(b"x" * 2000)) as save:
        with pytest.raises(ValidationError, match="remains too large"):
            PillowImageProcessor().process(photo_data, "image/jpeg", ImagePolicy(512, 100))
        assert save.call_count == 5


photo_data = photo((64, 64))


@pytest.mark.parametrize("data,mime", [
    (b"\xff\xd8\xffspoofed", "image/jpeg"), (b"<svg/>", "image/png"),
    (photo_data, "image/png"), (photo_data, "image/heic"),
    (photo_data[:-20], "image/jpeg"), (b"x" * (5 * 1024 * 1024 + 1), "image/jpeg"),
], ids=["spoof", "svg", "mime-mismatch", "unsupported-heic", "truncated", "oversized"])
def test_malformed_spoofed_unsupported_and_oversized_inputs(data, mime):
    with pytest.raises(ValidationError):
        PillowImageProcessor().process(data, mime, ImagePolicy(512, 512000))


def test_decompression_limits():
    with pytest.raises(ValidationError, match="dimensions"):
        PillowImageProcessor(max_pixels=100).process(photo_data, "image/jpeg", ImagePolicy(512, 512000))


def gateway():
    gw = R2StorageGateway(Settings(_env_file=None, environment="test", r2_account_id="test",
        r2_access_key_id="test", r2_secret_access_key="test-secret", r2_bucket="images",
        r2_public_url="https://cdn.example.test", public_api_base_url="https://api.example.test"))
    gw._client = MagicMock()
    return gw


@pytest.mark.parametrize("path,edge", [
    ("avatars/user/avatar.jpeg", 512), ("staff-photos/salon/staff/photo.jpeg", 1024),
    ("salon-images/salon/photo.jpeg", 1600),
])
async def test_client_bypass_is_processed_before_r2_publication(path, edge):
    gw = gateway()
    url = await gw.get_upload_url("images", path, "image/jpeg")
    assert url.startswith("https://api.example.test/v1/media/uploads/")
    gw._client.generate_presigned_url.assert_not_called()
    original = photo()
    await gw.accept_upload(url.rsplit("/", 1)[-1], original, "image/jpeg")
    args = gw._client.put_object.call_args.kwargs
    assert args["Body"] != original
    assert args["Key"] == path and args["ContentType"] == "image/jpeg"
    with Image.open(BytesIO(args["Body"])) as image:
        assert max(image.size) == edge


async def test_gateway_rejects_expiry_tampering_and_wrong_mime_before_r2():
    gw = gateway()
    token = (await gw.get_upload_url("images", "avatars/user/avatar.jpeg", "image/jpeg")).rsplit("/", 1)[-1]
    for candidate, mime in [(token + "x", "image/jpeg"), (token, "image/png")]:
        with pytest.raises(ValidationError):
            await gw.accept_upload(candidate, photo_data, mime)
    with patch("app.infrastructure.r2.storage.time.time", return_value=10**12), pytest.raises(ValidationError):
        await gw.accept_upload(token, photo_data, "image/jpeg")
    gw._client.put_object.assert_not_called()


async def test_gateway_rejects_bad_metadata_keys_and_buckets():
    gw = gateway()
    for bucket, path, mime in [("other", "avatars/u/a.jpeg", "image/jpeg"),
        ("images", "avatars/u/a.png", "image/jpeg"), ("images", "unknown/u/a.jpeg", "image/jpeg"),
        ("images", "avatars/../a.jpeg", "image/jpeg")]:
        with pytest.raises(ValidationError):
            await gw.get_upload_url(bucket, path, mime)
    gw._client.put_object.assert_not_called()


async def test_oversized_gateway_body_never_creates_object():
    gw = gateway()
    url = await gw.get_upload_url("images", "salon-images/salon/photo.jpeg", "image/jpeg")
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    register_exception_handlers(app)
    app.dependency_overrides[get_storage_gateway] = lambda: gw
    client = TestClient(app)
    response = client.put(url.replace("https://api.example.test", ""),
        content=b"x" * (5 * 1024 * 1024 + 1), headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 422
    response = client.put(url.replace("https://api.example.test", ""),
        content=iter([b"x" * 1024 * 1024] * 6), headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 422
    gw._client.put_object.assert_not_called()


async def test_failed_avatar_publication_defers_cleanup_until_committed_reference_check():
    repo, storage = AsyncMock(), AsyncMock()
    repo.update_profile.side_effect = RuntimeError("database failure")
    storage.upload_bytes.return_value = "https://cdn.example.test/new.jpeg"
    with pytest.raises(RuntimeError):
        await UploadAvatar(repo, storage, PillowImageProcessor()).execute(make_profile(), photo_data, "image/jpeg", "images")
    storage.delete_object.assert_not_awaited()
    repo.lock_media_url.assert_awaited_once_with("https://cdn.example.test/new.jpeg")


async def test_media_does_not_use_redis():
    # Assert against the actual cache adapter, not a fictitious media cache.
    from app.infrastructure.cache.redis import RedisCache
    with patch.object(RedisCache, "set", new_callable=AsyncMock) as cache_write:
        repo, storage = AsyncMock(), AsyncMock()
        await UploadAvatar(repo, storage, PillowImageProcessor()).execute(make_profile(), photo_data, "image/jpeg", "images")
        gw = gateway()
        token = (await gw.get_upload_url("images", "avatars/u/a.jpeg", "image/jpeg")).rsplit("/", 1)[-1]
        await gw.accept_upload(token, photo_data, "image/jpeg")
        cache_write.assert_not_awaited()
