"""Bounded, metadata-free image decoding and encoding."""

import asyncio
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.application.ports.image_processor import ImagePolicy
from app.core.exceptions import ValidationError

SUPPORTED_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="image-decode")


class PillowImageProcessor:
    def __init__(self, max_pixels: int = 40_000_000, max_source_bytes: int = 5 * 1024 * 1024):
        self.max_pixels = max_pixels
        self.max_source_bytes = max_source_bytes

    async def process_async(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes:
        return await asyncio.get_running_loop().run_in_executor(
            _executor, partial(self.process, data, content_type, policy),
        )

    def process(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes:
        if not data or len(data) > self.max_source_bytes:
            raise ValidationError("Image must be between 1 byte and 5 MB")
        expected = SUPPORTED_FORMATS.get(content_type)
        if not expected:
            raise ValidationError("Upload a JPEG, PNG or WebP image; convert HEIC on your device first")
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
