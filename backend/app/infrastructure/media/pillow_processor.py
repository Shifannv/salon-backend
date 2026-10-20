"""Bounded, metadata-free image decoding and encoding."""

from __future__ import annotations

import asyncio
import hashlib
import threading
import warnings
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import BytesIO
from typing import Any, ClassVar

from app.application.ports.image_processor import (
    IMAGE_POLICY_VERSION,
    IMAGE_VARIANT_POLICIES,
    ImagePolicy,
    ProcessedImageFamily,
    ProcessedVariant,
)
from app.core.exceptions import ServiceUnavailableError, ValidationError

SUPPORTED_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="image-decode")
_admission = threading.BoundedSemaphore(4)
POLICY_VERSION = IMAGE_POLICY_VERSION
VARIANT_POLICIES = IMAGE_VARIANT_POLICIES


class PillowImageProcessor:
    # Only hashes of outputs produced by this process are trusted. No image bytes,
    # client flags or metadata are cached. Eviction/restart simply re-encodes.
    _approved_outputs: ClassVar[OrderedDict[tuple, None]] = OrderedDict()
    _approved_lock = threading.Lock()

    def __init__(
        self, max_pixels: int = 40_000_000, max_source_bytes: int = 5 * 1024 * 1024,
        processing_timeout: float = 15.0, max_pending: int = 4,
    ):
        if processing_timeout <= 0 or max_pending < 1:
            raise ValueError("Image processing timeout and capacity must be positive")
        self.max_pixels = max_pixels
        self.max_source_bytes = max_source_bytes
        self.processing_timeout = processing_timeout
        self._admission = _admission if max_pending == 4 else threading.BoundedSemaphore(max_pending)

    async def _run_bounded(self, operation, *args):
        if not self._admission.acquire(blocking=False):
            raise ServiceUnavailableError("Image processing is busy; retry shortly")
        try:
            future = _executor.submit(partial(operation, *args))
        except BaseException:
            self._admission.release()
            raise
        # A timed-out/cancelled request cannot stop a running decoder. Keep its
        # admission slot occupied until the actual worker finishes.
        future.add_done_callback(lambda _: self._admission.release())
        wrapped = asyncio.wrap_future(future)
        # Consume failures even when the request has already timed out.
        wrapped.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        try:
            return await asyncio.wait_for(asyncio.shield(wrapped), self.processing_timeout)
        except TimeoutError as exc:
            raise ServiceUnavailableError("Image processing timed out; retry shortly") from exc

    async def process_async(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes:
        return await self._run_bounded(self.process, data, content_type, policy)

    async def process_family_async(
        self, data: bytes, content_type: str, category: str,
    ) -> ProcessedImageFamily:
        return await self._run_bounded(self.process_family, data, content_type, category)

    def process_family(self, data: bytes, content_type: str, category: str) -> ProcessedImageFamily:
        category = {"salon": "gallery", "service": "gallery"}.get(category, category)
        policies = VARIANT_POLICIES.get(category)
        if policies is None:
            raise ValidationError("Unsupported image category")
        clean = self._decode_clean(data, content_type)
        try:
            variants = tuple(self._encode_variant(clean, name, policy) for name, policy in policies)
            return ProcessedImageFamily(POLICY_VERSION, variants)
        finally:
            clean.close()

    def _decode_clean(self, data: bytes, content_type: str) -> Any:
        from PIL import Image, ImageOps, UnidentifiedImageError

        if not data or len(data) > self.max_source_bytes:
            raise ValidationError("Image exceeds the upload byte limit")
        expected = SUPPORTED_FORMATS.get(content_type)
        if expected is None:
            raise ValidationError("Upload a JPEG, PNG or WebP image")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                # verify validates container integrity without decoding pixels.
                with Image.open(BytesIO(data), formats=list(SUPPORTED_FORMATS.values())) as probe:
                    if probe.format != expected:
                        raise ValidationError("Content type does not match image bytes")
                    if probe.width * probe.height > self.max_pixels or max(probe.size) > 16384:
                        raise ValidationError("Image dimensions exceed the safe decoding limit")
                    if getattr(probe, "n_frames", 1) != 1:
                        raise ValidationError("Animated images are not supported")
                    probe.verify()
                with Image.open(BytesIO(data)) as source:
                    source.load()
                    oriented = ImageOps.exif_transpose(source)
                    try:
                        alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                        mode = "RGBA" if alpha else "RGB"
                        clean = Image.new(mode, oriented.size)
                        with oriented.convert(mode) as pixels:
                            clean.paste(pixels)
                        return clean
                    finally:
                        oriented.close()
        except ValidationError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValidationError("Malformed or unsupported image") from exc

    @staticmethod
    def _encode_variant(clean: Any, name: str, policy: ImagePolicy) -> ProcessedVariant:
        from PIL import Image

        for attempt in range(5):
            edge = max(1, int(policy.max_dimension * 0.8 ** attempt))
            with clean.copy() as candidate:
                candidate.thumbnail((edge, edge), Image.Resampling.LANCZOS)
                output = BytesIO()
                candidate.save(output, format="WEBP", quality=84 - attempt * 8, method=4, exact=True)
                data = output.getvalue()
                if len(data) <= policy.max_bytes:
                    return ProcessedVariant(name, candidate.width, candidate.height, data)
        raise ValidationError("Image remains too large after bounded compression; choose a smaller photo")

    def process(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes:
        if not data or len(data) > self.max_source_bytes:
            raise ValidationError("Image must be between 1 byte and 5 MB")
        expected = SUPPORTED_FORMATS.get(content_type)
        if not expected:
            raise ValidationError("Upload a JPEG, PNG or WebP image; convert HEIC on your device first")
        key = (hashlib.sha256(data).digest(), content_type, policy, self.max_pixels)
        with self._approved_lock:
            if key in self._approved_outputs:
                self._approved_outputs.move_to_end(key)
                return data
        # Imported on first use to keep Pillow and its native libraries out of cold start.
        from PIL import Image, ImageOps, UnidentifiedImageError

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data), formats=list(SUPPORTED_FORMATS.values())) as probe:
                    if probe.format != expected:
                        raise ValidationError("Content type does not match image bytes")
                    if probe.width * probe.height > self.max_pixels or max(probe.size) > 16384:
                        raise ValidationError("Image dimensions exceed the safe decoding limit")
                    if getattr(probe, "n_frames", 1) != 1:
                        raise ValidationError("Animated images are not supported")
                    probe.verify()
                with Image.open(BytesIO(data)) as source:
                    source.load()
                    oriented = ImageOps.exif_transpose(source)
                    # Fresh pixels remove EXIF, GPS, comments and ancillary metadata.
                    alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                    if expected == "JPEG" and alpha:
                        raise ValidationError("JPEG cannot preserve transparency")
                    mode = "RGBA" if alpha else "RGB"
                    clean = Image.new(mode, oriented.size)
                    clean.paste(oriented.convert(mode))
                    try:
                        for attempt in range(5):
                            edge = max(1, int(policy.max_dimension * 0.8 ** attempt))
                            candidate = clean.copy()
                            try:
                                candidate.thumbnail((edge, edge), Image.Resampling.LANCZOS)
                                output = BytesIO()
                                options = {"optimize": True} if expected in {"JPEG", "PNG"} else {}
                                if expected != "PNG":
                                    options["quality"] = 84 - attempt * 8
                                candidate.save(output, format=expected, **options)
                                result = output.getvalue()
                                if len(result) <= policy.max_bytes:
                                    output_key = (hashlib.sha256(result).digest(), content_type, policy, self.max_pixels)
                                    with self._approved_lock:
                                        self._approved_outputs[output_key] = None
                                        self._approved_outputs.move_to_end(output_key)
                                        while len(self._approved_outputs) > 256:
                                            self._approved_outputs.popitem(last=False)
                                    return result
                            finally:
                                candidate.close()
                    finally:
                        clean.close()
                        oriented.close()
        except ValidationError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValidationError("Malformed or unsupported image") from exc
        raise ValidationError("Image remains too large after bounded compression; choose a smaller photo")
