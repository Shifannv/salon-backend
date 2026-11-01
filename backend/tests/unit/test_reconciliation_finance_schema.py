"""Reconciliation must verify the tables that the finance migration creates."""
import re
from pathlib import Path

from scripts.migrations.reconciliation_harness import check_0051_finance_schema


class Catalog:
    def __init__(self, tables):
        self.tables = tables

    async def fetchrow(self, query, table):
        return {"exists": 1} if table in self.tables else None


def finance_tables():
    source = Path(__file__).parents[2] / "migrations/sql/0051_owner_finance_cashbook.sql"
    return set(re.findall(r"CREATE TABLE public\.(\w+)", source.read_text()))


async def test_finance_schema_accepts_actual_migration_tables():
    result = await check_0051_finance_schema(Catalog(finance_tables()))
    assert result["status"] == "PASS"


async def test_finance_schema_rejects_missing_day_close_table():
    result = await check_0051_finance_schema(Catalog(finance_tables() - {"salon_day_closes"}))
    assert result["status"] == "FAIL"
    assert {row["table"] for row in result["tables"] if not row["exists"]} == {"public.salon_day_closes"}
