"""Guards against a SQLAlchemy/asyncpg pitfall that unit tests can't otherwise catch.

Every other test in this suite mocks PlatformRepository outright (see
tests/conftest.py::make_mock_repo), so a raw-SQL bug inside it is invisible until a real
Postgres connection hits it. This test runs with no database at all: it only asks
SQLAlchemy to *compile* every raw query literal in the repository, which is enough to
reproduce the failure mode without a live DB.

Root cause (found 2026-08-13 by replaying get_booking()'s exact query against the real
DB): SQLAlchemy's text() bind-parameter parser does not recognize `:name` when it is
immediately followed by a Postgres `::type` cast -- `:actor_id::uuid` silently fails to
register as a bind parameter at all, so asyncpg receives literal `:actor_id::uuid` in the
final SQL and rejects it with "syntax error at or near ':'". This broke get_booking() for
every non-null actor_id -- i.e. every create_booking/approve/reject/complete/cancel/
record_payment call, since each one calls get_booking() to build its response. `cast(:name
as type)` compiles correctly and is the fix; a bare `:name` compared directly against a
typed column also compiles fine since Postgres infers the type from context.
"""

import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql.asyncpg import dialect as asyncpg_dialect

# The actual production dialect (app/infrastructure/db/session.py uses the asyncpg driver).
# Its paramstyle is numeric ($1, $2, ...), unlike the generic postgresql.dialect()'s
# pyformat -- the bug only reproduces against the dialect the app actually uses.
_DIALECT = asyncpg_dialect()

REPOSITORY_PATH = (
    Path(__file__).parent.parent
    / "app"
    / "infrastructure"
    / "db"
    / "repositories"
    / "platform_repository.py"
)

# A bind parameter immediately followed by `::` -- the exact shape that fails to compile.
_UNSAFE_CAST_PATTERN = re.compile(r":[a-zA-Z_][a-zA-Z0-9_]*::")


def _sql_string_literals() -> list[str]:
    """Extract every triple-quoted string in the repository source as a raw-SQL candidate.

    Overshoots (also matches docstrings), but that's fine for a lexical guard: a docstring
    containing this pattern is not something we'd want anyway, and every real query in this
    file is written as `text(\"\"\"...\"\"\")`.
    """

    source = REPOSITORY_PATH.read_text()
    return re.findall(r'"""(.*?)"""', source, re.DOTALL)


def test_no_bind_param_is_immediately_followed_by_a_pg_cast():
    """Lexical guard: `:name::type` breaks SQLAlchemy's asyncpg compilation; `cast(:name as
    type)` does not. Catches the whole class of bug file-wide, not just get_booking().
    """

    offenders = [
        (i, s) for i, s in enumerate(_sql_string_literals()) if _UNSAFE_CAST_PATTERN.search(s)
    ]
    assert offenders == [], (
        "Found `:param::type` in platform_repository.py -- SQLAlchemy's text() bind-param "
        "parser does not recognize a name immediately followed by `::`, so asyncpg receives "
        "it as literal, unparseable SQL. Use `cast(:param as type)` instead."
    )


def test_reference_repro_of_the_broken_pattern():
    """Documents *why* the guard above exists, against the real production dialect
    (asyncpg's paramstyle is numeric `$1, $2, ...`, not the generic dialect's pyformat --
    the bug only reproduces against the dialect the app actually uses).

    `:a::uuid` never becomes a recognized bind parameter at all: the compiled SQL text is
    unchanged and asyncpg receives the literal `:a::uuid`, which is what produces
    "syntax error at or near ':'" against a real DB.
    """

    compiled = text("select :a::uuid as x").compile(dialect=_DIALECT)
    assert str(compiled) == "select :a::uuid as x"  # never substituted
    assert compiled.params == {}  # "a" was never recognized as a bind parameter


def test_reference_cast_function_form_compiles_correctly():
    """The fix, proven the same way: `cast(:a as uuid)` compiles to a real `$1` placeholder."""

    compiled = text("select cast(:a as uuid) as x").compile(dialect=_DIALECT)
    assert str(compiled) == "select cast($1 as uuid) as x"
    assert compiled.params == {"a": None}
