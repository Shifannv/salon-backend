"""Compare a disposable local Alembic-head catalog with Mumbai, read-only remotely."""

import asyncio
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

import asyncpg
import httpx

from migration_mumbai_staging_20261015 import CA_URL, HOST, REF, ROOT, config_values

BIN = Path("C:/Program Files/PostgreSQL/18/bin")
CATALOG = """
select jsonb_build_object(
 'tables',(select jsonb_object_agg(c.relname,jsonb_build_object('rls',c.relrowsecurity,'replica_identity',c.relreplident)) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r'),
 'columns',(select jsonb_object_agg(c.relname||'.'||a.attname,jsonb_build_object('type',format_type(a.atttypid,a.atttypmod),'not_null',a.attnotnull,'default',pg_get_expr(d.adbin,d.adrelid),'generated',a.attgenerated,'identity',a.attidentity)) from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where n.nspname='public' and c.relkind='r' and a.attnum>0 and not a.attisdropped),
 'constraints',(select jsonb_object_agg(c.relname||'.'||k.conname,pg_get_constraintdef(k.oid)) from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'),
 'indexes',(select jsonb_object_agg(indexname,indexdef) from pg_indexes where schemaname='public'),
 'functions',(select jsonb_object_agg(p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',jsonb_build_object('body',p.prosrc,'result',pg_get_function_result(p.oid),'language',l.lanname,'volatility',p.provolatile,'security_definer',p.prosecdef,'config',p.proconfig)) from pg_proc p join pg_namespace n on n.oid=p.pronamespace join pg_language l on l.oid=p.prolang where n.nspname='public' and not exists(select 1 from pg_depend d where d.classid='pg_proc'::regclass and d.objid=p.oid and d.deptype='e')),
 'triggers',(select jsonb_object_agg(n.nspname||'.'||c.relname||'.'||t.tgname,pg_get_triggerdef(t.oid)) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where not t.tgisinternal and (n.nspname='public' or (n.nspname='auth' and c.relname='users'))),
 'policies',(select jsonb_object_agg(tablename||'.'||policyname,jsonb_build_object('cmd',cmd,'roles',roles,'permissive',permissive,'using',qual,'check',with_check)) from pg_policies where schemaname='public'),
 'enums',(select jsonb_object_agg(typname,labels) from (select t.typname,jsonb_agg(e.enumlabel order by e.enumsortorder) labels from pg_type t join pg_namespace n on n.oid=t.typnamespace join pg_enum e on e.enumtypid=t.oid where n.nspname='public' group by t.typname)x)
)
"""


def command(args, **kwargs):
    # Background PostgreSQL children can inherit pipe handles on Windows. Files
    # avoid communicate() waiting for those children to close captured pipes.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=output,
                                stderr=errors, timeout=120, check=False,
                                creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)
        output.seek(0)
        text = output.read().decode("utf-8", errors="replace")
        errors.seek(0)
        error_text = errors.read().decode("utf-8", errors="replace")
    if result.returncode:
        # Local PostgreSQL/Alembic output only; child environment has no remote DSN.
        raise RuntimeError((error_text or text)[-5000:])
    return text


def migration_sql(url, revision):
    env = dict(os.environ, DATABASE_URL=url, ENVIRONMENT="local", PYTHONIOENCODING="utf-8",
               PAYMENT_PROVIDER="none", SUBSCRIPTION_PROVIDER="none", CASHFREE_ENABLED="false")
    return command([sys.executable, "-m", "alembic", "upgrade", revision, "--sql"],
                   cwd=ROOT / "backend", env=env)


def normalize(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, dict):
        return {key: normalize(val) for key, val in value.items()}
    if isinstance(value, list):
        return [normalize(val) for val in value]
    return value


async def compare(port):
    local_url = f"postgresql://postgres@127.0.0.1:{port}/postgres"
    local = await asyncpg.connect(local_url)
    await local.execute("""
      create role anon; create role authenticated; create role service_role bypassrls;
      create schema auth;
      create table auth.users(id uuid primary key,email text,phone text,
        raw_user_meta_data jsonb not null default '{}',raw_app_meta_data jsonb not null default '{}');
      create function auth.uid() returns uuid language sql stable as $$
        select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid
      $$;
      create publication supabase_realtime;
    """)
    url = local_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(json.dumps({"stage": "building disposable local baseline through 0004"}), flush=True)
    await local.execute(migration_sql(url, "0004_service_duration_slot_steps"))
    # Existing integration fixture documents this consolidated-baseline overlap.
    await local.execute("alter table staff drop column experience")
    print(json.dumps({"stage": "building disposable local revisions 0005 through head"}), flush=True)
    await local.execute(migration_sql(url, "0004_service_duration_slot_steps:0033_payment_fee_snapshot"))
    # Preserve 0034's autocommit boundaries. A single multi-statement simple query
    # would otherwise wrap the enum additions in one implicit transaction.
    enum_sql = migration_sql(url, "0033_payment_fee_snapshot:0034_booking_lifecycle_states")
    for statement in enum_sql.split(";"):
        statement = re.sub(r"--[^\n]*", "", statement).strip()
        if statement and statement.upper() not in {"BEGIN", "COMMIT"}:
            await local.execute(statement)
    await local.execute(migration_sql(url, "0034_booking_lifecycle_states:head"))
    head = await local.fetchval("select version_num from public.alembic_version")
    assert head == "0037_customer_processing_charge"
    expected = json.loads(await local.fetchval(CATALOG))
    _values, parts = config_values()
    response = await asyncio.to_thread(httpx.get, CA_URL, timeout=15)
    response.raise_for_status()
    context = ssl.create_default_context()
    context.load_verify_locations(cadata=response.text)
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    remote = await asyncpg.connect(host=HOST, port=5432, database="postgres",
        user=f"postgres.{REF}", password=unquote(parts.password or ""), ssl=context,
        timeout=15, statement_cache_size=0)
    actual = json.loads(await remote.fetchval(CATALOG))
    differences = {}
    for category, expected_objects in expected.items():
        expected_objects = expected_objects or {}
        actual_objects = actual.get(category) or {}
        missing = sorted(expected_objects.keys() - actual_objects.keys())
        extra = sorted(actual_objects.keys() - expected_objects.keys())
        changed = {key: {"head": expected_objects[key], "mumbai": actual_objects[key]}
                   for key in expected_objects.keys() & actual_objects.keys()
                   if normalize(expected_objects[key]) != normalize(actual_objects[key])}
        differences[category] = {"missing": missing, "extra": extra, "changed": changed}
    artifact = {"destination": REF, "head": head, "reference_postgres": "18",
                "destination_postgres": "17", "normalization": "whitespace only",
                "acl_comparison": "excluded; restricted destination ACLs are intentional and separately reviewed",
                "differences": differences}
    path = ROOT / "backend/migrations/reviews/migration-mumbai-head-comparison-2026-10-15.json"
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps({"head": head, "differences": {k: {"missing": len(v['missing']),
        "extra": len(v['extra']), "changed": len(v['changed'])} for k,v in differences.items()},
        "artifact": path.name}, indent=2))
    await remote.close()
    await local.close()


if __name__ == "__main__":
    directory = Path(tempfile.mkdtemp(prefix="salon-mumbai-head-"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    started = False
    try:
        command([str(BIN / "initdb.exe"), "-D", str(directory / "data"), "-U", "postgres",
                 "--auth=trust", "--no-locale", "-E", "UTF8"])
        command([str(BIN / "pg_ctl.exe"), "-D", str(directory / "data"),
                 "-l", str(directory / "postgres.log"), "-o", f"-h 127.0.0.1 -p {port} -c wal_level=logical", "-w", "start"])
        started = True
        asyncio.run(compare(port))
    except Exception as exc:  # noqa: BLE001 -- CLI boundary must redact remote credentials.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__,
                          "local_diagnostic": str(exc) if isinstance(exc, (RuntimeError, asyncpg.PostgresError)) else None}))
        raise SystemExit(1) from None
    finally:
        if started and (directory / "data/postmaster.pid").exists():
            command([str(BIN / "pg_ctl.exe"), "-D", str(directory / "data"), "-m", "fast", "-w", "stop"])
        print(json.dumps({"local_disposable_directory": str(directory), "local_server_stopped": started}))
