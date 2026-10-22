"""Image processing port: no encoder dependencies in the application layer."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol


@dataclass(frozen=True)
class ImagePolicy:
    max_dimension: int
    max_bytes: int


IMAGE_POLICY_VERSION = "webp-v2"
IMAGE_VARIANT_POLICIES = {
    "avatar": (("avatar", ImagePolicy(512, 512000)),),
    "staff": (("card", ImagePolicy(512, 512000)), ("detail", ImagePolicy(1024, 1048576))),
    "gallery": (("thumbnail", ImagePolicy(400, 1048576)),
                ("card", ImagePolicy(800, 1048576)), ("detail", ImagePolicy(1600, 1048576))),
}


@dataclass(frozen=True)
class ProcessedVariant:
    name: str
    width: int
    height: int
    data: bytes
    mime: str = "image/webp"

    @property
    def sha256(self) -> str:
        return sha256(self.data).hexdigest()


@dataclass(frozen=True)
class ProcessedImageFamily:
    policy_version: str
    variants: tuple[ProcessedVariant, ...]


class ImageProcessor(Protocol):
    def process(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes: ...

    async def process_async(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes: ...

    def process_family(self, data: bytes, content_type: str, category: str) -> ProcessedImageFamily: ...

    async def process_family_async(
        self, data: bytes, content_type: str, category: str,
    ) -> ProcessedImageFamily: ...
