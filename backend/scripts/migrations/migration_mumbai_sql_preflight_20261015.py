"""Run exact approved 0038..0040 SQL inside BEGIN/ROLLBACK on Mumbai only.

No committed migration, Supabase history write or Alembic history/stamp operation.
Fresh verified backup is mandatory. Never call alembic upgrade on empty history.
"""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

from backend.scripts.migrations.migration_mumbai_reference_20261015 import CATALOG
from backend.scripts.migrations.migration_mumbai_staging_20261015 import (
    HOST,
    REF,
    ROOT,
    config_values,
)

PSQL = Path("C:/Program Files/PostgreSQL/18/bin/psql.exe")
FILES = [ROOT / "backend/migrations/sql" / name for name in (
    "0038_cancellation_compatibility.sql", "0039_promotion_search_path.sql",
    "0040_fastapi_only_access.sql",
)]

FINGERPRINT = """md5(jsonb_build_object(
 'application', (__CATALOG__),
 'relation_acls',(SELECT jsonb_agg(jsonb_build_object('oid',c.oid,'acl',c.relacl,'owner',c.relowner) ORDER BY c.oid)
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'function_acls',(SELECT jsonb_agg(jsonb_build_object('oid',p.oid,'acl',p.proacl,'owner',p.proowner,'config',p.proconfig) ORDER BY p.oid)
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'column_acls',(SELECT jsonb_agg(jsonb_build_object('table',a.attrelid,'num',a.attnum,'acl',a.attacl) ORDER BY a.attrelid,a.attnum)
    FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE a.attnum>0 AND NOT a.attisdropped AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'schema_acls',(SELECT jsonb_agg(jsonb_build_object('oid',oid,'owner',nspowner,'acl',nspacl) ORDER BY oid) FROM pg_namespace),
 'defaults',(SELECT jsonb_agg(to_jsonb(d) ORDER BY d.oid) FROM pg_default_acl d),
 'memberships',(SELECT jsonb_agg(to_jsonb(m) ORDER BY m.roleid,m.member,m.grantor) FROM pg_auth_members m),
 'alembic',(SELECT coalesce(jsonb_agg(version_num),'[]'::jsonb) FROM public.alembic_version),
 'auth_count',(SELECT count(*) FROM auth.users),
 'profiles',(SELECT count(*) FROM public.profiles),
 'bookings',(SELECT count(*) FROM public.bookings)
)::text)""".replace("__CATALOG__", CATALOG.strip().rstrip(";"))


def main():
    _values, parts = config_values()
    backups = sorted((ROOT / "supabase-schema-backup").glob("mumbai-pre-0038-0040-*/verification.json"))
    assert backups
    verification = backups[-1]
    backup = json.loads(verification.read_text())
    assert backup["destination"] == REF and backup["status"] == "verified_schema_only_backup"
    schema = ROOT / backup["schema_file"]
    assert hashlib.sha256(schema.read_bytes()).hexdigest() == backup["sha256"]
    seal = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-forward-files-2026-10-15.json").read_text())["files_sha256"]
    for file in FILES:
        assert hashlib.sha256(file.read_bytes()).hexdigest() == seal[file.relative_to(ROOT).as_posix()]
    sql = "\\set ON_ERROR_STOP on\n"
    sql += "DO $gate$ BEGIN IF current_database()<>'postgres' OR current_user<>'postgres' THEN RAISE EXCEPTION 'Unexpected database/user'; END IF; IF EXISTS(SELECT 1 FROM public.alembic_version) THEN RAISE EXCEPTION 'Alembic history is no longer empty'; END IF; END $gate$;\n"
    sql += "SELECT set_config('mumbai_preflight.before_hash', " + FINGERPRINT + ",false) IS NOT NULL AS snapshot_captured;\n"
    sql += "BEGIN;\n"
    for path in FILES:
        sql += "\\echo preflight_" + path.stem + "\n" + path.read_text(encoding="utf-8") + "\n"
    sql += "ROLLBACK;\n"
    sql += "DO $verify$ BEGIN IF " + FINGERPRINT + " IS DISTINCT FROM current_setting('mumbai_preflight.before_hash') THEN RAISE EXCEPTION 'Rollback fingerprint mismatch'; END IF; END $verify$;\n"
    sql += "SELECT 'passed' AS rollback_fingerprint, count(*) AS alembic_rows FROM public.alembic_version;\n"
    script = verification.parent / "rollback-preflight.sql"
    script.write_text(sql, encoding="utf-8")
    env = dict(os.environ)
    env.update(PGPASSWORD=unquote(parts.password or ""), PGSSLMODE="verify-full",
               PGSSLROOTCERT=str(verification.parent / "supabase-public-ca.crt"), PGCONNECT_TIMEOUT="15")
    args = [str(PSQL), "--no-psqlrc", "--no-password", "--host", HOST,
            "--port", "5432", "--username", f"postgres.{REF}", "--dbname", "postgres",
            "--file", str(script)]
    result = subprocess.run(args, env=env, capture_output=True, timeout=180, check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    # These files contain only supplied SQL labels, DDL status/metadata and server
    # diagnostics from reviewed metadata SQL, never connection secrets or user rows.
    output = result.stdout.decode("utf-8", errors="replace")
    error = result.stderr.decode("utf-8", errors="replace")
    passed = result.returncode == 0 and "passed" in output and "ROLLBACK" in output
    evidence = {"destination": REF, "status": "passed" if passed else "failed",
        "committed_migrations": False, "stamp_executed": False,
        "backup_sha256": backup["sha256"], "script": str(script.relative_to(ROOT)),
        "exit_code": result.returncode, "rollback_verified": passed,
        "SQL_labels_seen": [p.stem for p in FILES if "preflight_" + p.stem in output],
        "TLS": "libpq verify-full", "command": "psql --no-psqlrc --no-password --host <Mumbai pooler> --port 5432 --username <Mumbai project user> --dbname postgres --file <verified backup/rollback-preflight.sql>"}
    if not passed:
        # Persist only a SQLSTATE category or controlled preflight error label. Never
        # persist raw connection diagnostics, SQL error text or supplied parameters.
        evidence["diagnostic_class"] = "rollback_mismatch" if "Rollback fingerprint mismatch" in error else "SQL_or_connection_error"
        # SQL is fixed reviewed metadata/DDL only: expose just its ERROR summary,
        # never connection diagnostics, full SQL context or parameter values.
        summaries = re.findall(r"(?:ERROR|HINT):\s*([^\r\n]+)", error)
        evidence["SQL_error_summary"] = summaries[:3]
    (ROOT / "backend/migrations/reviews/migration-mumbai-execution-preflight-2026-10-15.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return passed


if __name__ == "__main__":
    try:
        ok = main()
    except Exception as exc:
        print(json.dumps({"status": "preflight_failed", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
    raise SystemExit(0 if ok else 1)
