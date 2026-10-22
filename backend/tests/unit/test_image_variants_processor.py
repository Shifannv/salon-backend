"""Synthetic image family processing and bounded execution; no storage access."""

import asyncio
import threading
from hashlib import sha256
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from app.application.ports.image_processor import ImagePolicy
from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.infrastructure.media.pillow_processor import PillowImageProcessor


def photo(size=(2000, 1000), *, alpha=False, orientation=None):
    with Image.new("RGBA" if alpha else "RGB", size, (70, 120, 190, 80) if alpha else (70, 120, 190)) as image:
        output = BytesIO()
        exif = Image.Exif()
        exif[270] = "private description"
        exif[34853] = {1: "N", 2: (1.0, 2.0, 3.0)}
        if orientation:
            exif[274] = orientation
        image.save(output, "PNG" if alpha else "JPEG", exif=exif)
        return output.getvalue()


@pytest.mark.parametrize("category,expected", [
    ("avatar", [("avatar", 512, 512000)]),
    ("staff", [("card", 512, 512000), ("detail", 1024, 1048576)]),
    ("gallery", [("thumbnail", 400, 1048576), ("card", 800, 1048576), ("detail", 1600, 1048576)]),
])
def test_variants_have_approved_dimensions_caps_webp_and_hashes(category, expected):
    processor = PillowImageProcessor()
    source = photo()
    family = processor.process_family(source, "image/jpeg", category)
    assert family.policy_version == "webp-v2"
    assert family == processor.process_family(source, "image/jpeg", category)
    assert len(family.variants) == len(expected)
    for variant, (name, edge, cap) in zip(family.variants, expected, strict=True):
        assert variant.name == name
        assert variant.mime == "image/webp"
        assert variant.sha256 == sha256(variant.data).hexdigest()
        assert len(variant.data) <= cap
        assert variant.data[:4] == b"RIFF" and variant.data[8:12] == b"WEBP"
        with Image.open(BytesIO(variant.data)) as image:
            assert image.size == (edge, edge // 2) == (variant.width, variant.height)
            assert not image.getexif()
            assert not any(key in image.info for key in ("exif", "icc_profile", "xmp"))


def test_transparency_small_source_and_orientation():
    processor = PillowImageProcessor()
    family = processor.process_family(photo((80, 40), alpha=True), "image/png", "gallery")
    for variant in family.variants:
        with Image.open(BytesIO(variant.data)) as image:
            assert image.size == (80, 40)
            assert image.getpixel((0, 0))[3] == 80
    oriented = processor.process_family(photo((800, 400), orientation=6), "image/jpeg", "avatar")
    assert (oriented.variants[0].width, oriented.variants[0].height) == (256, 512)


def test_source_pixels_are_loaded_once_for_all_variants():
    processor = PillowImageProcessor()
    with patch.object(processor, "_decode_clean", wraps=processor._decode_clean) as decode:
        assert len(processor.process_family(photo(), "image/jpeg", "gallery").variants) == 3
        decode.assert_called_once()


@pytest.mark.parametrize("kind", ["mime", "svg", "truncated", "malformed", "oversized", "animation"])
def test_reject_unsafe_sources(kind):
    data, mime = photo((80, 40)), "image/jpeg"
    if kind == "mime":
        mime = "image/png"
    elif kind == "svg":
        data = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2"/></svg>'
    elif kind == "truncated":
        data = data[:-20]
    elif kind == "malformed":
        data = b"garbage"
    elif kind == "oversized":
        data = b"x" * (5 * 1024 * 1024 + 1)
    elif kind == "animation":
        output = BytesIO()
        with Image.new("RGB", (16, 16), "red") as first, Image.new("RGB", (16, 16), "blue") as second:
            first.save(output, "WEBP", save_all=True, append_images=[second], duration=100)
        data, mime = output.getvalue(), "image/webp"
    with pytest.raises(ValidationError):
        PillowImageProcessor().process_family(data, mime, "gallery")


def test_pixel_limit_and_pillow_bomb_warning():
    source = photo((80, 40))
    with pytest.raises(ValidationError, match="dimensions"):
        PillowImageProcessor(max_pixels=100).process_family(source, "image/jpeg", "avatar")
    with patch.object(Image, "MAX_IMAGE_PIXELS", 2000), pytest.raises(ValidationError, match="Malformed"):
        PillowImageProcessor().process_family(source, "image/jpeg", "avatar")


def test_bounded_variant_encoding_rejects_unsatisfiable_cap():
    with (
        Image.new("RGB", (64, 64)) as image,
        patch.object(Image.Image, "save", side_effect=lambda output, **kw: output.write(b"x" * 2000)) as save,
    ):
        with pytest.raises(ValidationError, match="remains too large"):
            PillowImageProcessor._encode_variant(image, "card", ImagePolicy(512, 100))
        assert save.call_count == 5


@pytest.mark.asyncio
async def test_timeout_keeps_capacity_until_worker_finishes_and_legacy_shares_queue():
    processor = PillowImageProcessor(processing_timeout=0.05, max_pending=1)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def blocked(*args):
        entered.set()
        try:
            release.wait(2)
            return b"done"
        finally:
            finished.set()

    try:
        with patch.object(processor, "process", side_effect=blocked):
            request = asyncio.create_task(processor.process_async(b"input", "image/jpeg", ImagePolicy(512, 512000)))
            assert await asyncio.to_thread(entered.wait, 1)
            with pytest.raises(ServiceUnavailableError, match="timed out"):
                await request
            with pytest.raises(ServiceUnavailableError, match="busy"):
                await processor.process_family_async(b"input", "image/jpeg", "avatar")
        release.set()
        assert await asyncio.to_thread(finished.wait, 1)
        # Callback runs immediately after the worker returns. Await the shared
        # semaphore outside the event loop to establish completion without sleep.
        assert await asyncio.to_thread(processor._admission.acquire, True, 1)
        processor._admission.release()
        family = await processor.process_family_async(photo((32, 16)), "image/jpeg", "avatar")
        assert family.variants[0].width == 32
    finally:
        release.set()
