"""Realistic SQLAlchemy database errors for repository tests.

SQLAlchemy's asyncpg adapter wraps a PostgreSQL error in a ``DBAPIError`` whose ``orig``
carries the SQLSTATE as ``sqlstate`` (and ``pgcode``). A business error raised by
``raise exception '...'`` in a SQL function uses SQLSTATE ``P0001``.
"""

from sqlalchemy.exc import DBAPIError, InternalError, OperationalError


class _PgError(Exception):
    def __init__(self, message: str, sqlstate: str | None) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate
        self.pgcode = sqlstate


def business_error(message: str, sqlstate: str = "P0001") -> DBAPIError:
    """A deliberate rejection: ``raise exception`` (P0001) or the checkout guard trigger (23514)."""

    return InternalError("select create_booking(...)", {}, _PgError(message, sqlstate))


def infrastructure_error(message: str, sqlstate: str | None = None) -> DBAPIError:
    """A connection, pool or server failure: not a business error."""

    return OperationalError("select create_booking(...)", {}, _PgError(message, sqlstate))
