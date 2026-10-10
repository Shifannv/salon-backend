"""Validate the subscription migration works with asyncpg's prepared statements."""

import importlib.util
from pathlib import Path
from unittest.mock import patch


def test_upgrade_executes_each_top_level_ddl_statement_separately():
    path = Path(__file__).resolve().parents[2] / "migrations/versions/0018_subscription_foundation.py"
    spec = importlib.util.spec_from_file_location("subscription_foundation_revision", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    statements = []
    with patch.object(migration.op, "execute", side_effect=statements.append):
        migration.upgrade()

    assert len(statements) == 17
    assert all(statement.lower().count("create ") == 1 for statement in statements)
    assert any("create table subscription_plans" in statement for statement in statements)
    assert any("create trigger t_subscription_plans_audit" in statement for statement in statements)
    assert any("create table salon_subscriptions" in statement for statement in statements)
    assert any("create trigger t_salon_subscriptions_audit" in statement for statement in statements)
    assert any("create index idx_salon_subscriptions_salon_id" in statement for statement in statements)
    assert any("create index idx_salon_subscriptions_status" in statement for statement in statements)
    assert any("create table subscription_events" in statement for statement in statements)
    assert any("create index idx_subscription_events_subscription" in statement for statement in statements)
