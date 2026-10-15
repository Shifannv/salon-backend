"""Build review-only Mumbai SQL and privilege evidence from sanitized local artifacts.

No network, environment loading, database connection or SQL execution.
"""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "backend/migrations/reviews/migration-mumbai-review-2026-10-15"
CLIENTS = ("PUBLIC", "anon", "authenticated")
TABLE_PRIVILEGES = (
    "SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER", "MAINTAIN",
)
HEADER = """-- REVIEW ONLY / NOT EXECUTED / NOT AN ALEMBIC REVISION.
-- Destination: wqjlgpnbiapcrlkxumcp, ap-south-1 ONLY.
-- Independently verify the project before connection; shared pooler host is not identity.
-- Requires separate user approval. No data/history/stamp/deployment operations.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
SET LOCAL search_path = pg_catalog, public;
"""


def write(name, content):
    (OUT / name).write_text(content, encoding="utf-8")


def build():
    OUT.mkdir(exist_ok=True)
    snapshot = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-least-privilege-snapshot-2026-10-15.json").read_text())
    audit = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-completion-audit-2026-10-15.json").read_text())
    comparison = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-head-comparison-2026-10-15.json").read_text())
    functions = sorted(snapshot["functions"], key=lambda item: item["signature"])
    tables = sorted(snapshot["tables"], key=lambda item: item["name"])
    assert len(functions) == 52 and len(tables) == 44
    assert all(t["kind"] == "r" and t["owner"] == "postgres" and t["rls"] for t in tables)
    signatures = ["public." + f["signature"].replace("booking_source", "public.booking_source")
                  .replace("subscription_status", "public.subscription_status")
                  .replace("(salon_payout_accounts)", "(public.salon_payout_accounts)")
                  for f in functions]
    schema = HEADER + """
-- Adopt both legacy compatibility columns in a FUTURE expected head; never delete them.
-- Release gate: erasure classification/tests must cover both fields before a real
-- Alembic revision is created. This SQL does not implement erasure or authorize writes.
DO $review$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'bookings'
          AND column_name IN ('cancellation_reason_code', 'cancellation_reason_text')
          AND (data_type <> 'text' OR udt_schema <> 'pg_catalog' OR udt_name <> 'text'
               OR is_nullable <> 'YES' OR column_default IS NOT NULL
               OR is_generated <> 'NEVER' OR is_identity <> 'NO'
               OR domain_name IS NOT NULL OR collation_name IS NOT NULL)
    ) THEN
        RAISE EXCEPTION 'Compatibility-column definition differs; abort';
    END IF;
END
$review$;
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_code text;
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_text text;
-- Current Mumbai already contains both definitions: expected destination delta is zero.
-- No constraint, index, function body, trigger, grant, RLS policy or data change.
COMMIT;
"""
    write("01-schema-only.sql", schema)
    guards = """
-- Guard NAMED objects, extension membership, owners, RLS and column ACLs.
-- Full inventory/body/config equality is a separate pre-execution comparison gate.
DO $review$
DECLARE obj oid;
BEGIN
"""
    for t in tables:
        guards += f"""    obj := to_regclass('public.{t['name']}');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.{t['name']}';
    END IF;
"""
    for sig in signatures:
        guards += f"""    obj := to_regprocedure('{sig}');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: {sig}';
    END IF;
"""
    guards += "END\n$review$;\n"
    guards += """
-- Capture retained effective server access, including inherited PUBLIC/client rights.
-- Transaction-local metadata only; not a table, persistent setting or future default.
DO $review$
BEGIN
    PERFORM set_config('mumbai_review.server_effective_before', (
        SELECT coalesce(jsonb_agg(right_to_keep), '[]'::jsonb)::text FROM (
            SELECT jsonb_build_object('kind', 'table', 'object', c.oid::regclass::text,
                'role', r.name, 'privilege', v.privilege) AS right_to_keep
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            CROSS JOIN (VALUES ('postgres'), ('service_role')) AS r(name)
            CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'),
                ('TRUNCATE'), ('REFERENCES'), ('TRIGGER'), ('MAINTAIN')) AS v(privilege)
            WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND NOT EXISTS (SELECT 1 FROM pg_depend d
                  WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
              AND has_table_privilege(r.name, c.oid, v.privilege)
            UNION ALL
            SELECT jsonb_build_object('kind', 'sequence', 'object', c.oid::regclass::text,
                'role', r.name, 'privilege', v.privilege)
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            CROSS JOIN (VALUES ('postgres'), ('service_role')) AS r(name)
            CROSS JOIN (VALUES ('USAGE'), ('SELECT'), ('UPDATE')) AS v(privilege)
            WHERE n.nspname = 'public' AND c.relkind = 'S'
              AND NOT EXISTS (SELECT 1 FROM pg_depend d
                  WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
              AND has_sequence_privilege(r.name, c.oid, v.privilege)
            UNION ALL
            SELECT jsonb_build_object('kind', 'function', 'object', p.oid::regprocedure::text,
                'role', r.name, 'privilege', 'EXECUTE')
            FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            CROSS JOIN (VALUES ('postgres'), ('service_role')) AS r(name)
            WHERE n.nspname = 'public'
              AND NOT EXISTS (SELECT 1 FROM pg_depend d
                  WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e')
              AND has_function_privilege(r.name, p.oid, 'EXECUTE')
        ) AS rights
    ), true);
END
$review$;
"""
    rows = []
    security = HEADER + guards + """
-- Existing NAMED application objects only. No managed extension objects included.
-- No role, schema, default-privilege or future-object changes. RESTRICT is deliberate.
-- postgres owns these objects; its backend sessions need no additional GRANT.
"""
    for table in tables:
        name = f"public.{table['name']}"
        security += f"REVOKE ALL PRIVILEGES ON TABLE {name} FROM PUBLIC, anon, authenticated RESTRICT;\n"
        for role in CLIENTS:
            for privilege in TABLE_PRIVILEGES:
                rows.append(["REVOKE", name, role, privilege,
                             "FastAPI owns data access; deny direct client table access",
                             "yes", "no", "already absent in observed Mumbai ACL"])
    for sig in signatures:
        security += f"REVOKE EXECUTE ON FUNCTION {sig} FROM PUBLIC, anon, authenticated RESTRICT;\n"
        for role in CLIENTS:
            rows.append(["REVOKE", sig, role, "EXECUTE",
                         "Prevent direct client RPC; preserve server/trigger execution",
                         "yes", "no", "already absent in observed Mumbai ACL"])
    # Named, already-existing server grants from the reviewed backend-only contract.
    for name, reason in (
        ("create_booking", "Preserve explicit server-only booking RPC contract from revision 0024"),
        ("get_available_slots", "Preserve explicit server-only availability RPC contract"),
    ):
        sig = signatures[[f["name"] for f in functions].index(name)]
        security += f"GRANT EXECUTE ON FUNCTION {sig} TO service_role;\n"
        rows.append(["GRANT", sig, "service_role", "EXECUTE", reason,
                     "yes", "no", "already granted; no new authority on observed Mumbai"])
    security += """
-- Config-only hardening; body, owner, volatility and SECURITY mode unchanged.
ALTER FUNCTION public.is_subscription_promotion_active(
    public.subscription_status, timestamptz, timestamptz, timestamptz, timestamptz
) SET search_path = public;
"""
    security += "DO $review$\nDECLARE retained jsonb;\nBEGIN\n"
    # Effective-role checks catch inherited client privileges on named objects.
    for t in tables:
        name = f"public.{t['name']}"
        for role in CLIENTS[1:]:
            for privilege in TABLE_PRIVILEGES:
                security += f"    IF has_table_privilege('{role}', '{name}', '{privilege}') THEN RAISE EXCEPTION 'Effective client privilege remains: {role} {name} {privilege}'; END IF;\n"
    for sig in signatures:
        for role in CLIENTS[1:]:
            security += f"    IF has_function_privilege('{role}', '{sig}', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: {role} {sig}'; END IF;\n"
    security += """
    FOR retained IN SELECT value FROM jsonb_array_elements(
        current_setting('mumbai_review.server_effective_before')::jsonb)
    LOOP
        IF NOT (CASE retained->>'kind'
            WHEN 'table' THEN has_table_privilege(retained->>'role', retained->>'object', retained->>'privilege')
            WHEN 'sequence' THEN has_sequence_privilege(retained->>'role', retained->>'object', retained->>'privilege')
            WHEN 'function' THEN has_function_privilege(retained->>'role', retained->>'object', retained->>'privilege')
            ELSE false END) THEN
            RAISE EXCEPTION 'Retained effective server access was lost: %', retained;
        END IF;
    END LOOP;
"""
    security += "END\n$review$;\nCOMMIT;\n"
    write("02-security-grants.sql", security)
    with (OUT / "privilege-matrix.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["operation", "object", "grantee", "privilege", "reason",
                         "existing_objects_only", "future_objects_receive_privilege", "observed_delta"])
        writer.writerows(rows)
    signup = HEADER + """
-- Reuse reviewed 0024 function. Do not recreate it, change its body or grant clients EXECUTE.
-- Snapshot body MD5 is a drift guard, not a replacement for reviewed source comparison.
DO $review$
DECLARE fn oid := to_regprocedure('public.handle_new_user()');
BEGIN
    IF fn IS NULL OR NOT EXISTS (
        SELECT 1 FROM pg_proc WHERE oid = fn AND proowner = 'postgres'::regrole
          AND prosecdef AND prorettype = 'trigger'::regtype
          AND proconfig = ARRAY['search_path=public']::text[]
          AND md5(prosrc) = 'bbc4006b3b60009d8f7ff6cdd89f71df'
    ) THEN RAISE EXCEPTION 'Signup function differs from reviewed backup/0024'; END IF;
    IF has_schema_privilege('anon', 'public', 'CREATE')
       OR has_schema_privilege('authenticated', 'public', 'CREATE') THEN
        RAISE EXCEPTION 'Untrusted role can create public objects';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'auth.users'::regclass
        AND tgname = 't_on_auth_user_created') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger
            WHERE tgrelid = 'auth.users'::regclass AND tgname = 't_on_auth_user_created'
              AND NOT tgisinternal AND tgtype = 5 AND tgfoid = fn AND tgenabled = 'O'
              AND tgqual IS NULL AND tgattr::text = '' AND tgargs = ''::bytea
              AND tgconstraint = 0 AND tgparentid = 0
              AND tgoldtable IS NULL AND tgnewtable IS NULL) THEN
            RAISE EXCEPTION 'Existing signup trigger differs; never replace automatically';
        END IF;
    ELSE
        CREATE TRIGGER t_on_auth_user_created AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
    END IF;
END
$review$;
-- Existing matching trigger is retained. Expected Mumbai delta: no change.
-- No signup, INSERT, role assignment, function grant or user-data copying is performed.
COMMIT;
"""
    write("03-signup-trigger.sql", signup)
    differences = comparison["differences"]
    constraint = differences["constraints"]
    assert len(constraint["missing"]) == 317
    assert all(name.endswith("_not_null") for name in constraint["missing"])
    report = {
        "destination": snapshot["destination"], "repository_head": comparison["head"],
        "alembic_destination_rows": snapshot["alembic"],
        "comparison_provenance": "Earlier same-session PG18 clean-head comparison; migration sources unchanged; ACLs excluded from that comparison",
        "categories": differences,
        "constraint_interpretation": {
            "missing_pg18_not_null_catalog_entries": constraint["missing"],
            "missing_real_constraints_established": [],
            "equivalent_check_deparser_difference": constraint["changed"],
            "limit": "Column not-null flags match. PG17-vs-PG18 catalog differences are not a request to create constraints.",
        },
        "current_catalog": audit["catalog"],
        "current_exact_object_acls": {"functions": functions, "tables": tables},
        "defaults_unchanged": snapshot["defaults"],
        "supabase_history": snapshot["supabase_history"],
        "head_effective_acl_comparison": "Not captured by prior clean-head build; see exact source statement ledger; do not claim effective ACL equality",
    }
    write("exact-differences.json", json.dumps(report, indent=2) + "\n")
    # Preserve exact source ACL statements with line numbers, not inferred effective ACLs.
    ledger = []
    for path in [ROOT / "backend/migrations/sql/001_supabase_schema.sql",
                 *sorted((ROOT / "backend/migrations/versions").glob("*.py"))]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\b(grant|revoke)\s+|alter default privileges", line, re.IGNORECASE):
                ledger.append({"file": path.relative_to(ROOT).as_posix(), "line": number,
                               "source": line.strip(), "note": "Source excerpt; upgrade/downgrade and dynamic SQL context must be read in original file"})
    write("repository-acl-source-ledger.json", json.dumps(ledger, indent=2) + "\n")
    # Exact backup client ACL SQL lines with their observed destination state.
    backup_rows = []
    for number, line in enumerate((ROOT / "supabase-schema-backup/schema.sql").read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("GRANT ") or not any(f'TO "{r}";' in line for r in CLIENTS[1:]):
            continue
        match = re.search(r'ON (TABLE|FUNCTION) "public"\."([^"]+)"', line)
        if match and ((match[1] == "TABLE" and match[2] in {t["name"] for t in tables})
                      or (match[1] == "FUNCTION" and match[2] in {f["name"] for f in functions})):
            backup_rows.append({"backup_line": number, "source_grant": line,
                                "destination": "absent; intentionally not proposed for restoration"})
    write("backup-client-grant-differences.json", json.dumps(backup_rows, indent=2) + "\n")
    print(json.dumps({"files": sorted(p.name for p in OUT.iterdir()), "privilege_rows": len(rows),
                      "backup_client_grants_absent": len(backup_rows)}))


if __name__ == "__main__":
    build()
