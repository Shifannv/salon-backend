"""Row helpers shared by SQL repositories."""

from typing import Any

from sqlalchemy.engine import Result


def one_dict_or_none(result: Result[Any]) -> dict[str, Any] | None:
    """Return the single mapped row as a plain dict, or ``None`` when no row matched."""
    row = result.mappings().one_or_none()
    return dict(row) if row else None
