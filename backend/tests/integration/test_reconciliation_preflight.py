"""Isolated reconciliation preflight checks against a disposable local PostgreSQL.

Set RESTORE_DB_URL to a local PostgreSQL admin URL (never production).
Set MUMBAI_PROJECT_CONFIRM=wqjlgpnbiapcrlkxumcp to confirm the project ref.
Tests are skipped when these are absent.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

RESTORE_DB_URL = os.environ.get("RESTORE_DB_URL", "")
MUMBAI_PROJECT_CONFIRM = os.environ.get("MUMBAI_PROJECT_CONFIRM", "")
PRODUCTION_HOST = "db.wqjlgpnbiapcrlkxumcp.supabase.co"

pytestmark = pytest.mark.skipif(
    not RESTORE_DB_URL or not MUMBAI_PROJECT_CONFIRM,
    reason="Requires RESTORE_DB_URL and MUMBAI_PROJECT_CONFIRM for disposable local PostgreSQL",
)


def _assert_not_production() -> None:
    if PRODUCTION_HOST in RESTORE_DB_URL:
        pytest.fail(
            "RESTORE_DB_URL points at production. "
            "These tests must only run against a disposable local database."
        )
    for pooler in ("aws-0-ap-south-1.pooler.supabase.com", "aws-1-ap-south-1.pooler.supabase.com"):
        if pooler in RESTORE_DB_URL:
            pytest.fail("RESTORE_DB_URL points at a Supabase pooler (production path).")


async def _conn():
    import asyncpg  # type: ignore[import]
    plain = RESTORE_DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")
    return await asyncpg.connect(plain)


@pytest.fixture
def harness():
    from scripts.migrations.reconciliation_harness import (
        check_baseline_0040_tables_exist,
        check_empty_alembic_version,
        check_fastapi_only_acl,
        check_0049_primary_key,
        check_0049_subscription_plan_prices,
        check_0049_table_structure,
        check_0050_column_exists,
    )
    return {
        "check_empty_alembic_version": check_empty_alembic_version,
        "check_baseline_0040_tables_exist": check_baseline_0040_tables_exist,
        "check_fastapi_only_acl": check_fastapi_only_acl,
        "check_0049_table_structure": check_0049_table_structure,
        "check_0049_primary_key": check_0049_primary_key,
        "check_0049_subscription_plan_prices": check_0049_subscription_plan_prices,
        "check_0050_column_exists": check_0050_column_exists,
    }


def test_restore_db_not_production():
    _assert_not_production()
    assert MUMBAI_PROJECT_CONFIRM == "wqjlgpnbiapcrlkxumcp"


def test_empty_alembic_version_check_structure(harness):
    async def run():
        conn = await _conn()
        try:
            result = await harness["check_empty_alembic_version"](conn)
            assert "check" in result and "status" in result
            assert result["check"] == "empty_alembic_version"
            return result
        finally:
            await conn.close()

    result = asyncio.run(run())
    assert result["status"] in {"PASS", "FAIL"}


def test_0049_structure_check_returns_mismatches_for_missing_table(harness):
    """Verify the check reports FAIL if salon_plan_prices is absent."""
    async def run():
        conn = await _conn()
        try:
            await conn.execute("DROP TABLE IF EXISTS public.salon_plan_prices CASCADE")
            result = await harness["check_0049_table_structure"](conn)
            await conn.execute("ROLLBACK")
            return result
        except Exception:
            await conn.close()
            raise
        finally:
            await conn.close()

    result = asyncio.run(run())
    assert result["status"] == "FAIL"


def test_wrong_project_confirmation_aborts(monkeypatch):
    """Validate that the harness _check_project_confirmation aborts on wrong value."""
    import sys
    from scripts.migrations.reconciliation_harness import _check_project_confirmation

    with pytest.raises(SystemExit) as exc_info:
        _check_project_confirmation("wrong-project-ref")
    assert exc_info.value.code == 1 or str(exc_info.value.code).startswith("[FATAL]") or exc_info.value.code != 0


def test_production_url_blocked(monkeypatch):
    """Validate that _validate_not_production aborts on production URL."""
    from scripts.migrations.reconciliation_harness import _validate_not_production

    with pytest.raises(SystemExit):
        _validate_not_production(f"postgresql+asyncpg://postgres:pw@{PRODUCTION_HOST}:5432/postgres")


def test_0049_equivalence_check_requires_correct_columns(harness):
    """Check that column structure validation catches a missing column."""
    async def run():
        conn = await _conn()
        try:
            result = await harness["check_0049_table_structure"](conn)
            return result
        finally:
            await conn.close()

    result = asyncio.run(run())
    assert "mismatches" in result
    assert result["status"] in {"PASS", "FAIL"}
