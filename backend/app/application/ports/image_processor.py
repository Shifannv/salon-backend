"""Image processing port: no encoder dependencies in the application layer."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ImagePolicy:
    max_dimension: int
    max_bytes: int


class ImageProcessor(Protocol):
    def process(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes: ...

    async def process_async(self, data: bytes, content_type: str, policy: ImagePolicy) -> bytes: ...
