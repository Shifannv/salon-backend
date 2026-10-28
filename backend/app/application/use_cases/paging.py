"""Paging arguments shared by list use cases."""

from typing import Any


def paging_kwargs(limit: int | None, offset: int) -> dict[str, Any]:
    """Return only the paging arguments the caller actually set.

    Omitted values let the repository apply its default safety ceiling
    (newest first, at most 1000 rows).
    """

    kwargs: dict[str, Any] = {}
    if limit is not None:
        kwargs["limit"] = limit
    if offset:
        kwargs["offset"] = offset
    return kwargs
