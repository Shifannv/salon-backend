"""Explicit GPS stripping and transient cleanup-provider failures."""

from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from app.application.use_cases.media_cleanup import retire_unreferenced_media
from app.core.exceptions import ValidationError
from app.infrastructure.media.admission import UploadAdmissionMiddleware
from app.infrastructure.media.pillow_processor import PillowImageProcessor
from tests.unit.media_r2_fake import FakeR2Client
from tests.unit.test_image_processing import gateway, photo_data
from tests.unit.test_media_admission import Downstream, invoke, scope


def test_actual_gps_exif_is_removed_from_every_variant():
    exif = Image.Exif()
    exif[274] = 6
    exif[34853] = {1: "N", 2: (12.0, 34.0, 56.0), 3: "E", 4: (77.0, 1.0, 2.0)}
    output = BytesIO()
    with Image.new("RGB", (900, 600), "blue") as image:
        image.save(output, "JPEG", exif=exif)
    source = output.getvalue()
    with Image.open(BytesIO(source)) as image:
        assert 34853 in image.getexif()
    family = PillowImageProcessor().process_family(source, "image/jpeg", "gallery")
    for variant in family.variants:
        with Image.open(BytesIO(variant.data)) as image:
            assert image.height > image.width
            assert not image.getexif()
            assert "exif" not in image.info


async def test_transient_head_failure_is_reported_not_silently_classed_as_legacy():
    storage = gateway()
    storage._client = FakeR2Client()
    token = (await storage.get_upload_url("images", "avatars/user-001/image.jpg", "image/jpeg")).rsplit("/", 1)[-1]
    result = await storage.accept_upload(token, photo_data, "image/jpeg")
    storage._client.head_object.side_effect = TimeoutError("Synthetic HEAD failure")
    references = AsyncMock()
    with pytest.raises(TimeoutError):
        await retire_unreferenced_media(references, storage, "images", result["public_url"].split(".test/")[1])
    storage._client.delete_object.assert_not_called()


async def test_raw_storage_helper_is_not_exposed_and_family_type_is_required():
    storage = gateway()
    assert not hasattr(storage, "upload_bytes")
    with pytest.raises(ValidationError, match="processed image family"):
        await storage.upload_processed_family("images", "avatars/user-001/", photo_data)
    storage._client.put_object.assert_not_called()


async def test_metadata_gets_share_admission_and_reject_request_bodies():
    downstream = Downstream()
    middleware = UploadAdmissionMiddleware(downstream, rate_limit=1)
    request = scope(path="/v1/media/results/synthetic", method="GET", headers=[])
    sent = await invoke(middleware, request, [{"type": "http.request", "body": b""}])
    assert sent[0]["status"] == 204
    sent = await invoke(middleware, request, [{"type": "http.request", "body": b""}])
    assert sent[0]["status"] == 429
    assert downstream.calls == 1
    sent = await invoke(UploadAdmissionMiddleware(downstream), request,
                        [{"type": "http.request", "body": b"unexpected"}])
    assert sent[0]["status"] == 413
    assert downstream.calls == 1


async def test_grant_json_is_bounded_before_parsing():
    downstream = Downstream()
    sent = await invoke(UploadAdmissionMiddleware(downstream),
                        scope(path="/v1/profiles/me/avatar-upload-url", method="POST",
                              headers=[(b"content-type", b"application/json")]),
                        [{"type": "http.request", "body": b"x" * 8193}])
    assert sent[0]["status"] == 413
    assert downstream.calls == 0
