"""Verified Mumbai schema-only backup. No SQL migration execution in this script."""

import asyncio
import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

import httpx

from migration_mumbai_staging_20261015 import CA_URL, HOST, REF, ROOT, config_values

PG_DUMP = Path("C:/Program Files/PostgreSQL/18/bin/pg_dump.exe")


def statements(sql):
    """Top-level lexical statement splitter: skip comments, strings and dollar bodies."""
    parts = []
    start = i = 0
    tag = None
    quoted = False
    identifier = False
    line_comment = False
    block_depth = 0
    while i < len(sql):
        if line_comment:
            if sql[i] == "\n":
                line_comment = False
            i += 1
            continue
        if block_depth:
            if sql.startswith("/*", i):
                block_depth += 1
                i += 2
            elif sql.startswith("*/", i):
                block_depth -= 1
                i += 2
            else:
                i += 1
            continue
        if tag:
            if sql.startswith(tag, i):
                i += len(tag)
                tag = None
            else:
                i += 1
            continue
        if quoted or identifier:
            terminator = "'" if quoted else '"'
            if sql[i] == terminator:
                if i + 1 < len(sql) and sql[i + 1] == terminator:
                    i += 2
                    continue
                quoted = identifier = False
            i += 1
            continue
        if sql.startswith("--", i):
            line_comment = True
            i += 2
            continue
        if sql.startswith("/*", i):
            block_depth = 1
            i += 2
            continue
        if sql[i] == "'":
            quoted = True
        elif sql[i] == '"':
            identifier = True
        elif sql[i] == "$" and (match := re.match(r"\$[A-Za-z_0-9]*\$", sql[i:])):
            tag = match.group()
            i += len(tag)
            continue
        elif sql[i] == ";":
            parts.append(sql[start:i + 1])
            start = i + 1
        i += 1
    assert not tag and not quoted and not identifier and not block_depth
    if sql[start:].strip():
        parts.append(sql[start:])
    return parts


async def backup():
    _values, parts = config_values()
    directory = ROOT / "supabase-schema-backup" / (
        "mumbai-pre-0038-0040-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    directory.mkdir(parents=True, exist_ok=False)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(CA_URL)
        response.raise_for_status()
    ca = directory / "supabase-public-ca.crt"
    ca.write_text(response.text, encoding="ascii")
    env = dict(os.environ)
    env.update(PGPASSWORD=unquote(parts.password or ""), PGSSLMODE="verify-full",
               PGSSLROOTCERT=str(ca), PGCONNECT_TIMEOUT="15",
               PGOPTIONS="-c statement_timeout=120000 -c lock_timeout=5000")
    path = directory / "schema.sql"
    args = [str(PG_DUMP), "--schema-only", "--no-password", "--quote-all-identifiers",
            "--lock-wait-timeout=5s", "--host", HOST, "--port", "5432",
            "--username", f"postgres.{REF}", "--dbname", "postgres", "--file", str(path)]
    process = await asyncio.to_thread(subprocess.run, args, env=env, capture_output=True,
                                     timeout=180, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
    # Never print stderr: connection errors could echo supplied parameters.
    if process.returncode:
        safe = {"destination": REF, "status": "backup_failed", "exit_code": process.returncode,
                "partial_backup_must_not_be_used": True,
                "diagnostic_class": "permission" if b"permission denied" in process.stderr else "pg_dump_failure"}
        (directory / "verification.json").write_text(json.dumps(safe, indent=2), encoding="utf-8")
        print(json.dumps(safe))
        return
    source = path.read_text(encoding="utf-8")
    top = statements(source)
    forbidden = []
    for number, sql in enumerate(top):
        sql = re.sub(r"--[^\n]*", "", sql)
        sql = re.sub(r"^\\(?:un)?restrict[^\n]*", "", sql, flags=re.MULTILINE).strip()
        if re.match(r"(?:COPY|INSERT\s+INTO|UPDATE|DELETE|MERGE|TRUNCATE)\b", sql, re.IGNORECASE):
            forbidden.append(number)
    assert not forbidden
    assert "PostgreSQL database dump complete" in source
    assert '"cancellation_reason_code" "text"' in source
    assert '"cancellation_reason_text" "text"' in source
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    manifest = {"destination": REF, "status": "verified_schema_only_backup",
        "scope": "all schemas visible to Mumbai postgres role; pg_dump schema-only, owners/ACLs retained",
        "schema_file": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
        "sha256": digest, "top_level_statements": len(top), "data_statements": forbidden,
        "normalized_schema_sha256": hashlib.sha256(re.sub(
            r"^\\(?:un)?restrict[^\n]*(?:\n|$)", "", source, flags=re.MULTILINE).encode()).hexdigest(),
        "TLS": "libpq verify-full with public Supabase CA", "password_output": False,
        "command_redacted": "pg_dump --schema-only --no-password --quote-all-identifiers --lock-wait-timeout=5s --host <Mumbai pooler> --port 5432 --username <Mumbai project user> --dbname postgres --file <backup/schema.sql>"}
    (directory / "verification.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (directory / "SHA256SUMS").write_text(f"{digest}  schema.sql\n", encoding="ascii")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(backup())
    except Exception as exc:  # noqa: BLE001 -- redact connection details and all secrets.
        print(json.dumps({"destination": REF, "status": "backup_failed", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
