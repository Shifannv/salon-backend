"""Verify migration wiring and reversibility without contacting a database."""

import importlib.util
from pathlib import Path
from unittest.mock import patch


def test_media_guard_migration_covers_all_references_and_preserves_baseline():
    path = Path(__file__).resolve().parents[2] / "migrations/versions/0020_media_reference_guards.py"
    spec = importlib.util.spec_from_file_location("media_guard_revision", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "0019_discovery_placement"
    assert len(migration.MEDIA_COLUMNS) == 7
    statements = []
    with patch.object(migration.op, "execute", side_effect=statements.append):
        migration.upgrade()
    guard = statements[0]
    assert "security invoker" in guard
    assert "pg_advisory_xact_lock(hashtextextended(media_url, 0))" in guard
    assert "current_user in ('anon', 'authenticated')" in guard
    for (table, column), statement in zip(migration.MEDIA_COLUMNS, statements[1:], strict=True):
        assert f"before insert or update on {table}" in statement
        assert f"guard_media_reference('{column}')" in statement
    statements.clear()
    with patch.object(migration.op, "execute", side_effect=statements.append):
        migration.downgrade()
    assert len(statements) == 8
    assert statements[-1] == "drop function if exists guard_media_reference();"
