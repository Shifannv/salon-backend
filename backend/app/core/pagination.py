"""Pagination helpers for limit/offset style responses."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PageParams:
    """Validated page parameters for limit/offset pagination."""

    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if self.offset < 0:
            raise ValueError("offset must not be negative")


def paginate(rows: list[dict[str, Any]], params: PageParams) -> list[dict[str, Any]]:
    """Slice rows to a page — used when the query does not handle offset natively.

    Most queries in this project pass limit/offset directly to SQL, so this
    helper is mainly for in-memory slicing in tests or small reference tables.
    """

    return rows[params.offset : params.offset + params.limit]


def build_page_meta(
    total: int, params: PageParams
) -> dict[str, int]:
    """Return a pagination metadata dict for embedding in list responses.

    Example::

        {
            "total": 142,
            "limit": 50,
            "offset": 50,
            "has_more": True,
        }
    """

    return {
        "total": total,
        "limit": params.limit,
        "offset": params.offset,
        "has_more": params.offset + params.limit < total,
    }
