"""Shared Pydantic field types for API schemas."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BeforeValidator, PlainSerializer


def _id_to_str(value: object) -> object:
    """Database drivers return UUID objects; the HTTP contract uses strings (None passes through)."""

    return str(value) if value is not None else None


def _uuid_to_str(value: object) -> object:
    """Convert only UUID instances; any other value is left for normal validation."""

    return str(value) if isinstance(value, UUID) else value


# Response id: any non-null value is stringified.
IdStr = Annotated[str, BeforeValidator(_id_to_str)]

# Response id: only UUID instances are stringified; other values still fail ``str`` validation.
UuidAsStr = Annotated[str, BeforeValidator(_uuid_to_str)]

# Request id: validated as a UUID (malformed -> 422) and handed on as the canonical string,
# so use cases and repositories keep receiving ``str``.
UuidParam = Annotated[UUID, PlainSerializer(str, return_type=str, when_used="always")]

# Money held as Decimal internally; JSON clients keep receiving a number (not Pydantic's default string).
MoneyNumber = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
