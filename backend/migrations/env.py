"""Alembic async environment."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.migration_policy import validate_migration_target

config = context.config
# ConfigParser treats percent signs as interpolation markers. Supabase pooler
# passwords are often URL-encoded and can contain ``%``, so escape it only for
# Alembic's ini-backed config value.
supplied_url = make_url(os.environ.get("DATABASE_URL") or settings.database_url)
if supplied_url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
    from alembic.util import CommandError
    raise CommandError("Migration database driver must be PostgreSQL asyncpg")
migration_database_url = supplied_url.set(
    drivername="postgresql+asyncpg"
).render_as_string(hide_password=False)
config.set_main_option("sqlalchemy.url", migration_database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = None


def guard_requested_migration() -> None:
    """Validate mutations before constructing an engine or emitting executable SQL."""
    from alembic.script import ScriptDirectory
    from alembic.util import CommandError

    # Configuring without a connection exposes raw operation options before any SQL.
    context.configure(url=migration_database_url, target_metadata=target_metadata)
    options = context.get_context().opts
    cli_command = getattr(config.cmd_opts, "cmd", (None,))[0]
    command_name = getattr(cli_command or options.get("fn"), "__name__", "unknown")
    if command_name in {"current", "display_version", "check"}:
        return
    destination = options.get("destination_rev")
    if destination in ("head", "heads"):
        raise CommandError("Implicit upgrade head is refused; name the portable CI revision or an explicitly approved Mumbai revision")
    if not os.environ.get("DATABASE_URL"):
        raise CommandError("Migration DATABASE_URL must be explicitly supplied in process environment; local .env/default URLs do not authorize execution")
    validate_migration_target(ScriptDirectory.from_config(config), destination, migration_database_url,
        context.get_x_argument(as_dictionary=True), command=command_name,
        starting_revision=options.get("starting_rev"), offline=context.is_offline_mode())


def run_migrations_offline() -> None:
    """Run migrations without a live database connection."""

    context.configure(
        url=migration_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run migrations with a live connection."""

    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    from alembic.util import CommandError

    from app.core.migration_policy import (
        PORTABLE_CI_REVISION,
        PREPARED_REVISIONS,
        RECONCILIATION_REVISIONS,
        portable_revisions,
    )
    arguments = context.get_x_argument(as_dictionary=True)
    current_heads = context.get_context().get_current_heads()
    if arguments.get("migration_policy") == "portable-ci" and any(
        revision not in portable_revisions(context.script) for revision in current_heads
    ):
        raise CommandError("Portable CI refuses prepared or unknown current revisions before traversal")
    if arguments.get("migration_policy") == "mumbai" and (
        len(current_heads) != 1
        or current_heads[0] not in {PORTABLE_CI_REVISION, *PREPARED_REVISIONS, *RECONCILIATION_REVISIONS}
    ):
        raise CommandError("Mumbai history is not reconciled to a reviewed starting revision; refuse execution and do not stamp")

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Create an async engine and run online migrations."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


guard_requested_migration()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
