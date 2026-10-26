"""Static revision boundary and account-deletion contract checks; no migration execution."""

import ast
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"
REVISIONS = (
    ("0038_cancellation_compatibility", "0037_customer_processing_charge"),
    ("0039_promotion_search_path", "0038_cancellation_compatibility"),
    ("0040_fastapi_only_access", "0039_promotion_search_path"),
)


@pytest.mark.parametrize(("revision", "parent"), REVISIONS)
def test_forward_chain_and_non_destructive_downgrade(revision, parent):
    tree = ast.parse((MIGRATIONS / "versions" / f"{revision}.py").read_text())
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id in ("revision", "down_revision")}
    assert values == {"revision": revision, "down_revision": parent}
    downgrade = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade")
    assert isinstance(downgrade.body[0], ast.Raise)


def test_schema_adoption_preserves_both_values_and_rejects_definition_drift():
    sql = (MIGRATIONS / "sql" / "0038_cancellation_compatibility.sql").read_text().lower()
    for field in ("cancellation_reason_code", "cancellation_reason_text"):
        assert f"add column if not exists {field} text" in sql
    assert "is_generated <> 'never'" in sql and "domain_name is not null" in sql
    assert not re.search(r"^\s*(drop|update|delete|insert|truncate)\b", sql, re.MULTILINE)


def test_search_path_changes_configuration_without_replacing_booking_functions():
    sql = (MIGRATIONS / "sql" / "0039_promotion_search_path.sql").read_text().lower()
    assert "alter function public.is_subscription_promotion_active(" in sql
    assert "set search_path = public" in sql and "not p.prosecdef" in sql
    assert "create or replace" not in sql


def test_security_has_no_positive_default_or_future_client_grants():
    sql = (MIGRATIONS / "sql" / "0040_fastapi_only_access.sql").read_text()
    code = re.sub(r"--[^\n]*", "", sql)
    assert not re.search(r"\bGRANT\b|ALTER\s+DEFAULT|ALL\s+(?:FUNCTIONS|TABLES)\s+IN\s+SCHEMA", code, re.IGNORECASE)
    assert len(re.findall(r"^REVOKE ALL PRIVILEGES ON TABLE public\.", sql, re.MULTILINE)) == 44
    assert len(re.findall(r"^REVOKE EXECUTE ON FUNCTION public\.", sql, re.MULTILINE)) == 52
    assert "REVOKE ALL PRIVILEGES ON TABLE public.bookings FROM PUBLIC, anon, authenticated RESTRICT" in sql
    assert "mumbai_review.server_effective_before" in sql
    assert "Retained effective server access was lost" in sql
    assert "IF NOT (CASE retained->>'kind'" in sql
    assert "ELSE false END) THEN" in sql
    assert "AND attacl IS NOT NULL" in sql


def test_both_columns_are_classified_as_scrubbed():
    source = ROOT / "tests/integration/test_account_deletion_sql.py"
    tree = ast.parse(source.read_text())
    classification = next(n.value for n in tree.body if isinstance(n, ast.AnnAssign)
                          and isinstance(n.target, ast.Name) and n.target.id == "COLUMN_TREATMENT")
    treatments = {key.value: value.id for key, value in zip(classification.keys, classification.values, strict=True)}
    assert treatments["bookings.cancellation_reason_code"] == "S"
    assert treatments["bookings.cancellation_reason_text"] == "S"


class RecordingSession:
    def __init__(self):
        self.statements = []
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        if "to_regclass('public.booking_customer_changes')" in str(statement):
            return SimpleNamespace(mappings=lambda: SimpleNamespace(one=lambda: {"has_audits": True, "can_scrub": True}))
        if "select tablename from pg_catalog.pg_tables" in str(statement):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=list))


@pytest.mark.asyncio
async def test_customer_clear_happens_before_profile_reference_detachment():
    session = RecordingSession()
    repo = SQLAccountDeletionRepository(session)
    await repo.erase_database("synthetic-customer", "customer")
    statements = [s.lower() for s, _ in session.statements]
    scrub = next(i for i, s in enumerate(statements) if "cancellation_reason_code = null" in s)
    detach = next(i for i, s in enumerate(statements) if "select erase_profile_references" in s)
    assert scrub < detach
    audit_scrub = next(i for i, s in enumerate(statements) if "select public.erase_booking_audit_personal_data" in s)
    assert audit_scrub < scrub
    assert "cancellation_reason_text = null" in statements[scrub]
    assert "where customer_id = :uid" in statements[scrub]
    assert session.statements[scrub][1]["uid"] == "synthetic-customer"
    session.commit.assert_awaited_once()


def test_owner_scope_also_matches_legacy_fields_when_other_reasons_are_empty():
    source = (ROOT / "app/infrastructure/db/repositories/account_deletion_repository.py").read_text()
    owner = source.split("async def _scrub_owner_business", 1)[1]
    assert "cancellation_reason_code = null, cancellation_reason_text = null" in owner
    assert "where salon_id in {owned}" in owner
    assert "cancellation_reason_code is not null or cancellation_reason_text is not null" in owner
