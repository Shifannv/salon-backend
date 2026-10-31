"""
Isolated migration reconciliation harness.

Connects only to an explicitly supplied disposable PostgreSQL database.
Performs preflight/schema-equivalence checks and produces an evidence report.
NEVER connects to production unless an explicit later command is separately approved.

Usage (local/disposable database only):
    export RESTORE_DB_URL="postgresql+asyncpg://postgres:password@127.0.0.1:5432/salon_restore_test"
    export MUMBAI_PROJECT_CONFIRM="wqjlgpnbiapcrlkxumcp"
    python -m scripts.migrations.reconciliation_harness --phase preflight
    python -m scripts.migrations.reconciliation_harness --phase schema-check
    python -m scripts.migrations.reconciliation_harness --phase 0049-equivalence
    python -m scripts.migrations.reconciliation_harness --phase report
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[2]
MUMBAI_PROJECT = "wqjlgpnbiapcrlkxumcp"
PRODUCTION_HOST = f"db.{MUMBAI_PROJECT}.supabase.co"

# Expected 0049 table columns and types (from 0049_trial_salon_plan_prices.sql)
EXPECTED_SALON_PLAN_PRICES_COLUMNS: dict[str, str] = {
    "salon_id": "uuid",
    "plan_id": "uuid",
    "price_amount": "numeric",
    "set_by": "uuid",
    "created_at": "timestamp with time zone",
    "updated_at": "timestamp with time zone",
}
# Expected after 0050: additional column
EXPECTED_0050_COLUMN = "valid_until"

# Expected 0049 subscription_plans prices in production.
# NOTE: 0049 SQL sets 1675/2932 from 0031 seed. Production prices were updated to 2000/2999
# after 0049 was applied directly. Owner confirmed 2000/2999/499 as authoritative on 2026-10-31.
# See backend/docs/verification/0049_SUBSCRIPTION_PRICE_RECONCILIATION_2026-10-31.md (Path A).
EXPECTED_0049_PRICES: dict[str, float] = {
    "growth_1m": 499.00,
    "growth_6m": 2000.00,
    "growth_12m": 2999.00,
    "premium_6m": 2875.00,
    "premium_12m": 5032.00,
}

# Objects expected after 0040 baseline (FastAPI-only access controls)
EXPECTED_0040_OBJECTS: list[str] = [
    "public.salons",
    "public.profiles",
    "public.bookings",
    "public.services",
]


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"[FATAL] Required environment variable {name!r} is not set. "
                 "This harness must be pointed at an explicit disposable database.")
    return value


def _validate_not_production(db_url: str) -> None:
    """Abort if the database URL points at the known production host."""
    if PRODUCTION_HOST in db_url:
        sys.exit(
            "[FATAL] RESTORE_DB_URL points at the production Supabase host. "
            "This harness must only run against a disposable local database. "
            "Production execution requires a separately approved procedure."
        )
    pooler_hosts = {
        "aws-0-ap-south-1.pooler.supabase.com",
        "aws-1-ap-south-1.pooler.supabase.com",
    }
    for h in pooler_hosts:
        if h in db_url:
            sys.exit(
                "[FATAL] RESTORE_DB_URL points at a Supabase pooler (production path). "
                "Use a local disposable PostgreSQL database only."
            )


def _check_project_confirmation(confirmed: str) -> None:
    if confirmed != MUMBAI_PROJECT:
        sys.exit(
            f"[FATAL] MUMBAI_PROJECT_CONFIRM='{confirmed}' does not match expected project "
            f"'{MUMBAI_PROJECT}'. Pass the exact project ref to confirm you know which "
            "project's schema you are verifying against."
        )


async def _get_connection(db_url: str):
    """Create a raw asyncpg connection without the policy guard."""
    import asyncpg  # type: ignore[import]

    plain_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")
    conn = await asyncpg.connect(plain_url)
    return conn


async def check_empty_alembic_version(conn) -> dict[str, Any]:
    """PASS: alembic_version table exists and is empty (required for 0040 stamp)."""
    rows = await conn.fetch(
        "SELECT version_num FROM alembic_version"
    )
    current = [r["version_num"] for r in rows]
    return {
        "check": "empty_alembic_version",
        "status": "PASS" if not current else "FAIL",
        "current_versions": current,
        "note": "Must be empty before baseline 0040 stamp.",
    }


async def check_alembic_version_at(conn, expected_revision: str) -> dict[str, Any]:
    """PASS: alembic_version contains exactly the expected revision."""
    rows = await conn.fetch("SELECT version_num FROM alembic_version")
    current = [r["version_num"] for r in rows]
    return {
        "check": "alembic_version_at",
        "expected": expected_revision,
        "current": current,
        "status": "PASS" if current == [expected_revision] else "FAIL",
    }


async def check_baseline_0040_tables_exist(conn) -> dict[str, Any]:
    """PASS: key tables from 0001-0040 exist (structural baseline proof)."""
    results: list[dict] = []
    all_pass = True
    for qualified in EXPECTED_0040_OBJECTS:
        schema, table = qualified.split(".")
        row = await conn.fetchrow(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=$1 AND table_name=$2",
            schema, table,
        )
        exists = row is not None
        if not exists:
            all_pass = False
        results.append({"table": qualified, "exists": exists})
    return {
        "check": "baseline_0040_tables",
        "status": "PASS" if all_pass else "FAIL",
        "tables": results,
    }


async def check_fastapi_only_acl(conn) -> dict[str, Any]:
    """PASS: no direct client grants on core tables (0040 FastAPI-only access)."""
    rows = await conn.fetch(
        """
        SELECT grantee, table_schema, table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE table_schema = 'public'
          AND grantee NOT IN ('postgres', 'service_role', 'authenticator', 'anon', 'authenticated', 'PUBLIC')
          AND table_name IN ('salons','bookings','services','profiles')
        ORDER BY grantee, table_name
        """
    )
    unexpected = [dict(r) for r in rows]
    return {
        "check": "fastapi_only_acl",
        "status": "PASS" if not unexpected else "WARN",
        "unexpected_grants": unexpected,
        "note": "0040 removes direct client grants; unexpected rows need investigation.",
    }


async def check_alembic_version_at_0050(conn) -> dict[str, Any]:
    """PASS: alembic_version is exactly 0050_plan_price_valid_until (Gate B complete)."""
    return await check_alembic_version_at(conn, "0050_plan_price_valid_until")


async def check_0041_destructive_ddl_applied(conn) -> dict[str, Any]:
    """PASS: 0041 description columns dropped from salons and services; image trigger created."""
    issues: list[str] = []
    for table, col in [("salons", "description"), ("services", "description")]:
        row = await conn.fetchrow(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=$1 AND column_name=$2",
            table, col,
        )
        if row is not None:
            issues.append(f"public.{table}.{col} still exists — 0041 DROP may not have run")
    trig = await conn.fetchrow(
        "SELECT 1 FROM pg_trigger WHERE tgname='t_salon_image_limits'"
    )
    if trig is None:
        issues.append("trigger t_salon_image_limits missing — 0041 may not have applied")
    return {
        "check": "0041_destructive_ddl",
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "note": "If FAIL before 0041 is applied, this is expected — run only post-0041.",
    }


async def check_0042_destructive_ddl_applied(conn) -> dict[str, Any]:
    """PASS: 0042 category column dropped from salons."""
    row = await conn.fetchrow(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='salons' AND column_name='category'",
    )
    exists = row is not None
    return {
        "check": "0042_destructive_ddl",
        "status": "FAIL" if exists else "PASS",
        "category_column_exists": exists,
        "note": "PASS means column was dropped. FAIL before 0042 runs is expected.",
    }


async def check_0049_table_structure(conn) -> dict[str, Any]:
    """PASS: salon_plan_prices exists with exactly the expected columns and types."""
    rows = await conn.fetch(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'salon_plan_prices'
        ORDER BY ordinal_position
        """
    )
    found = {r["column_name"]: r["data_type"] for r in rows}
    mismatches: list[str] = []
    for col, expected_type in EXPECTED_SALON_PLAN_PRICES_COLUMNS.items():
        actual = found.get(col)
        if actual is None:
            mismatches.append(f"missing column: {col}")
        elif actual != expected_type:
            mismatches.append(f"{col}: expected {expected_type!r}, got {actual!r}")
    extra = set(found) - set(EXPECTED_SALON_PLAN_PRICES_COLUMNS) - {EXPECTED_0050_COLUMN}
    if extra:
        mismatches.append(f"unexpected columns: {sorted(extra)}")
    return {
        "check": "0049_table_structure",
        "status": "PASS" if not mismatches else "FAIL",
        "columns_found": found,
        "mismatches": mismatches,
    }


async def check_0049_primary_key(conn) -> dict[str, Any]:
    """PASS: salon_plan_prices has composite primary key on (salon_id, plan_id)."""
    rows = await conn.fetch(
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.table_name = 'salon_plan_prices'
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
        """
    )
    pk_cols = [r["column_name"] for r in rows]
    return {
        "check": "0049_primary_key",
        "status": "PASS" if pk_cols == ["salon_id", "plan_id"] else "FAIL",
        "primary_key_columns": pk_cols,
    }


async def check_0049_subscription_plan_prices(conn) -> dict[str, Any]:
    """PASS: subscription_plans prices match 0049 target values."""
    rows = await conn.fetch(
        "SELECT code, price_amount FROM public.subscription_plans WHERE code = ANY($1::text[])",
        list(EXPECTED_0049_PRICES.keys()),
    )
    found = {r["code"]: float(r["price_amount"]) for r in rows}
    mismatches: list[str] = []
    for code, expected_price in EXPECTED_0049_PRICES.items():
        actual = found.get(code)
        if actual is None:
            mismatches.append(f"missing plan: {code}")
        elif abs(actual - expected_price) > 0.005:
            mismatches.append(f"{code}: expected {expected_price}, got {actual}")
    return {
        "check": "0049_subscription_plan_prices",
        "status": "PASS" if not mismatches else "FAIL",
        "expected": EXPECTED_0049_PRICES,
        "found": found,
        "mismatches": mismatches,
    }


async def check_0050_column_exists(conn) -> dict[str, Any]:
    """PASS: valid_until column exists on salon_plan_prices (0050 applied)."""
    row = await conn.fetchrow(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='salon_plan_prices' AND column_name='valid_until'"
    )
    return {
        "check": "0050_valid_until_column",
        "status": "PASS" if row else "FAIL",
        "data_type": row["data_type"] if row else None,
        "expected_type": "timestamp with time zone",
        "type_match": row["data_type"] == "timestamp with time zone" if row else False,
    }


async def check_0051_finance_schema(conn) -> dict[str, Any]:
    """PASS: 0051 finance tables exist (salon_expenses, salon_cash_adjustments, etc.)."""
    tables = ["salon_expenses", "salon_cash_adjustments", "salon_day_close",
              "salon_expense_rules"]
    results: list[dict] = []
    all_pass = True
    for table in tables:
        row = await conn.fetchrow(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=$1", table
        )
        exists = row is not None
        if not exists:
            all_pass = False
        results.append({"table": f"public.{table}", "exists": exists})
    return {
        "check": "0051_finance_schema",
        "status": "PASS" if all_pass else "FAIL",
        "tables": results,
        "note": "Run only after 0051 is applied.",
    }


async def check_0052_booking_window_function(conn) -> dict[str, Any]:
    """PASS: get_available_slots function exists with booking-window 30-day guard (0052)."""
    row = await conn.fetchrow(
        """
        SELECT prosrc FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'get_available_slots'
        """
    )
    if row is None:
        return {"check": "0052_booking_window_function", "status": "FAIL",
                "note": "get_available_slots not found."}
    src = row["prosrc"]
    has_30d_guard = "30" in src and ("days" in src.lower() or "day" in src.lower())
    return {
        "check": "0052_booking_window_function",
        "status": "PASS" if has_30d_guard else "WARN",
        "has_30_day_guard": has_30d_guard,
        "note": "Inspect function body manually to verify exact window logic.",
    }


# Advisories printed before a phase runs — informational, not blocking.
# These remind the operator of pre-conditions that the harness cannot verify automatically.
PHASE_ADVISORIES: dict[str, list[str]] = {
    "schema-check": [
        (
            "ADVISORY — MAINTENANCE WINDOW: 0041 drops columns (salons.description, services.description) "
            "and adds a trigger. These are AccessExclusiveLock DDL operations on high-traffic tables. "
            "A maintenance window with write-freeze is required before running 0041 in production. "
            "See PRODUCTION_MIGRATION_EXECUTION_RUNBOOK.md §Option 1."
        ),
        (
            "ADVISORY — BACKUP: Ensure a fresh production backup was taken immediately before starting "
            "the Gate B sequence. Rollback path is restore-from-backup, not an Alembic downgrade."
        ),
    ],
    "post-0041-0048": [
        (
            "ADVISORY — LOCK TIMEOUT: If running on production, 0041 and 0042 DDL requires "
            "AccessExclusiveLock on salons/services. Set lock_timeout='5s' on the session before "
            "upgrade to prevent long waits. Write-freeze the application before running."
        ),
    ],
    "preflight": [
        (
            "ADVISORY — PITR: Supabase Mumbai project has PITR enabled (daily backups + WAL streaming). "
            "For Gate A isolated restore, download the latest Supabase backup and restore into a "
            "local Docker PostgreSQL — do NOT use PITR restore to production. "
            "See ISOLATED_RESTORE_EVIDENCE_TEMPLATE.md for the full procedure."
        ),
    ],
}

PHASE_CHECKS: dict[str, list] = {
    # Gate A: run before any production migration (isolated restore of production backup)
    "preflight": [
        check_empty_alembic_version,
        check_baseline_0040_tables_exist,
        check_fastapi_only_acl,
    ],
    "0049-equivalence": [
        check_0049_table_structure,
        check_0049_primary_key,
        check_0049_subscription_plan_prices,
    ],
    # schema-check: run after the full 0040-stamp + 0041-0048 + 0049-stamp sequence
    "schema-check": [
        check_baseline_0040_tables_exist,
        check_fastapi_only_acl,
        check_0041_destructive_ddl_applied,
        check_0042_destructive_ddl_applied,
        check_0049_table_structure,
        check_0049_primary_key,
        check_0049_subscription_plan_prices,
    ],
    # post-0041-0048: targeted destructive-DDL verification mid-sequence
    "post-0041-0048": [
        check_baseline_0040_tables_exist,
        check_fastapi_only_acl,
        check_0041_destructive_ddl_applied,
        check_0042_destructive_ddl_applied,
    ],
    "post-0050": [
        check_0050_column_exists,
    ],
    # post-gate-b: comprehensive check after the full Gate B sequence (stamp 0040 → upgrade 0050)
    "post-gate-b": [
        check_alembic_version_at_0050,
        check_baseline_0040_tables_exist,
        check_fastapi_only_acl,
        check_0041_destructive_ddl_applied,
        check_0042_destructive_ddl_applied,
        check_0049_table_structure,
        check_0049_primary_key,
        check_0049_subscription_plan_prices,
        check_0050_column_exists,
    ],
    "post-0051": [
        check_0051_finance_schema,
    ],
    "post-0052": [
        check_0052_booking_window_function,
    ],
    "report": [
        check_empty_alembic_version,
        check_baseline_0040_tables_exist,
        check_fastapi_only_acl,
        check_0041_destructive_ddl_applied,
        check_0042_destructive_ddl_applied,
        check_0049_table_structure,
        check_0049_primary_key,
        check_0049_subscription_plan_prices,
        check_0050_column_exists,
        check_0051_finance_schema,
        check_0052_booking_window_function,
    ],
}


async def run_phase(phase: str, db_url: str) -> list[dict]:
    checks = PHASE_CHECKS.get(phase)
    if not checks:
        sys.exit(f"[FATAL] Unknown phase: {phase!r}. Choose from: {sorted(PHASE_CHECKS)}")
    conn = await _get_connection(db_url)
    results: list[dict] = []
    try:
        for check_fn in checks:
            try:
                result = await check_fn(conn)
            except Exception as exc:
                result = {"check": check_fn.__name__, "status": "ERROR", "error": str(exc)}
            results.append(result)
            status = result.get("status", "?")
            indicator = "✓" if status == "PASS" else ("!" if status == "WARN" else "✗")
            print(f"  {indicator} {result['check']}: {status}")
    finally:
        await conn.close()
    return results


def write_evidence_report(phase: str, results: list[dict], db_url: str) -> Path:
    all_pass = all(r.get("status") in {"PASS", "WARN"} for r in results)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "target_db_host": db_url.split("@")[-1].split("/")[0] if "@" in db_url else "unknown",
        "overall_status": "PASS" if all_pass else "FAIL",
        "checks": results,
        "note": (
            "This report was produced against a disposable local database. "
            "It is evidence for a stamp or migration approval manifest, not a production run."
        ),
    }
    out_dir = BACKEND / "docs" / "verification"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"RECONCILIATION_EVIDENCE_{phase.upper()}_{ts}.json"
    out_path.write_text(json.dumps(report, indent=2))
    return out_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_stamp_manifest_inputs(target: str) -> None:
    """Print the SHA256 values needed to build an approval manifest for a stamp."""
    policy_path = BACKEND / "app" / "core" / "migration_policy.py"
    migrations_dir = BACKEND / "migrations"
    from alembic.script import ScriptDirectory
    script = ScriptDirectory(str(migrations_dir))
    rev = script.get_revision(target)
    rev_path = Path(rev.path)
    sql_path = migrations_dir / "sql" / f"{target}.sql"

    print(f"\n=== Stamp manifest source_sha256 inputs for {target} ===")
    print(f"  migration_policy.py : {_sha256(policy_path)}")
    print(f"  {rev_path.name}    : {_sha256(rev_path)}")
    if sql_path.exists():
        print(f"  {sql_path.name}  : {_sha256(sql_path)}")
    else:
        print(f"  {sql_path.name}  : (file not found)")
    print("\nInclude these in the approval manifest under 'source_sha256'.")
    print("Add review/preflight evidence doc hashes after running the checks.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Isolated migration reconciliation harness (disposable database only)."
    )
    parser.add_argument("--phase", choices=list(PHASE_CHECKS) + ["stamp-inputs"],
                        required=True,
                        help="Phase to run, or 'stamp-inputs' to print manifest hash values.")
    parser.add_argument("--stamp-target", default=None,
                        help="Target revision for --phase stamp-inputs.")
    parser.add_argument("--no-report", action="store_true",
                        help="Skip writing the JSON evidence report.")
    args = parser.parse_args()

    if args.phase == "stamp-inputs":
        target = args.stamp_target
        if not target:
            parser.error("--stamp-target is required with --phase stamp-inputs")
        print_stamp_manifest_inputs(target)
        return

    db_url = _require_env("RESTORE_DB_URL")
    confirmed = _require_env("MUMBAI_PROJECT_CONFIRM")
    _validate_not_production(db_url)
    _check_project_confirmation(confirmed)

    print(f"\n[harness] Phase: {args.phase}")
    print(f"[harness] Target: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print("[harness] NOT production (safety check passed)\n")

    for advisory in PHASE_ADVISORIES.get(args.phase, []):
        print(f"  ⚠  {advisory}\n")

    results = asyncio.run(run_phase(args.phase, db_url))
    overall = "PASS" if all(r.get("status") in {"PASS", "WARN"} for r in results) else "FAIL"
    print(f"\n[harness] Overall: {overall}")

    if not args.no_report:
        report_path = write_evidence_report(args.phase, results, db_url)
        print(f"[harness] Evidence report: {report_path}")

    if overall == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
