"""Reconciliation must verify the tables that the finance migration creates."""
import re
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from scripts.migrations.reconciliation_harness import (
    check_0049_subscription_plan_prices,
    check_0051_finance_schema,
    check_0052_booking_window_function,
)


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


@pytest.mark.parametrize("change", [None, "wrong_price", "missing_plan"])
async def test_subscription_prices_match_owner_confirmed_november_catalog(change):
    prices = {
        "growth_1m": 449,
        "growth_6m": 2419,
        "growth_12m": 4299,
        "premium_6m": 3499,
        "premium_12m": 6199,
    }
    if change == "wrong_price":
        prices["growth_1m"] = 499
    elif change == "missing_plan":
        prices.pop("premium_12m")
    connection = AsyncMock()
    connection.fetch.return_value = [
        {"code": code, "price_amount": value} for code, value in prices.items()
    ]
    result = await check_0049_subscription_plan_prices(connection)
    assert result["status"] == ("PASS" if change is None else "FAIL")
    assert bool(result["mismatches"]) == (change is not None)


@pytest.mark.parametrize("change", [None, "old_window", "missing_booking", "missing_availability"])
async def test_booking_window_requires_both_exact_approved_function_bodies(change):
    source = Path(__file__).parents[2] / "migrations/sql/0052_booking_window_30_days.sql"
    functions = re.findall(
        r"create or replace function public\.(\w+)\(.*?as \$\$(.*?)\$\$;",
        source.read_text(), re.IGNORECASE | re.DOTALL,
    )
    rows = [{"proname": name, "prosrc": body} for name, body in functions]
    assert {row["proname"] for row in rows} == {"get_available_slots", "create_booking"}
    if change == "old_window":
        rows[0]["prosrc"] = rows[0]["prosrc"].replace("v_today + 60", "v_today + 30")
    elif change == "missing_booking":
        rows = [row for row in rows if row["proname"] != "create_booking"]
    elif change == "missing_availability":
        rows = [row for row in rows if row["proname"] != "get_available_slots"]
    connection = AsyncMock()
    connection.fetch.return_value = rows
    result = await check_0052_booking_window_function(connection)
    assert result["status"] == ("PASS" if change is None else "FAIL")
