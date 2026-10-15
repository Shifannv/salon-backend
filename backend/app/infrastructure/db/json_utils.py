"""JSON helpers shared by SQL repositories."""

import json
from typing import Any


def decode_json(value: Any) -> Any:
    """Return a decoded JSON value; asyncpg can hand back jsonb as text or as Python objects."""
    return json.loads(value) if isinstance(value, str) else value
