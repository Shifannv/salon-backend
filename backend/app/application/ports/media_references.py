"""Coordinate publication with cleanup without changing the database schema."""

from typing import Protocol


class MediaReferences(Protocol):
    async def lock_media_url(self, url: str) -> None: ...

    async def media_url_is_referenced(self, url: str) -> bool: ...
