"""Sanitized Mumbai connection/catalog audit. No migration or remote schema writes."""

import asyncio
import hashlib
import json
import ssl
import statistics
import time
from urllib.parse import unquote

import asyncpg
import httpx
from backend.scripts.migrations.migration_mumbai_reference_20261015 import CATALOG
from backend.scripts.migrations.migration_mumbai_staging_20261015 import (
    CA_URL,
    HOST,
    REF,
    ROOT,
    config_values,
)


def distribution(values):
    return {"samples_ms": values, "median_ms": round(statistics.median(values), 3),
            "p95_nearest_rank_ms": max(values), "n": len(values)}


async def audit():
    _values, parts = config_values()
    async with httpx.AsyncClient(timeout=20) as client:
        ca = await client.get(CA_URL)
        ca.raise_for_status()
    tls = ssl.create_default_context()
    tls.load_verify_locations(cadata=ca.text)
    tls.verify_flags &= ~ssl.VERIFY_X509_STRICT
    assert tls.verify_mode == ssl.CERT_REQUIRED and tls.check_hostname
    options = {"host": HOST, "port": 5432, "user": f"postgres.{REF}", "database": "postgres",
               "password": unquote(parts.password or ""), "ssl": tls, "timeout": 15,
               "statement_cache_size": 0}
    connect_times = []
    for _ in range(10):
        started = time.perf_counter()
        connection = await asyncpg.connect(**options)
        connect_times.append(round((time.perf_counter() - started) * 1000, 3))
        await connection.close()
    connection = await asyncpg.connect(**options)
    try:
        identity = dict(await connection.fetchrow("""select current_database() database,
            current_user actor,current_setting('server_version') version"""))
        upstream_tls = await connection.fetchrow("select ssl,version,cipher from pg_stat_ssl where pid=pg_backend_pid()")
        latency = {}
        for label, query in (("select_1", "select 1"),
                             ("simple_read", "select count(*) from public.languages")):
            samples = []
            for _ in range(10):
                started = time.perf_counter()
                await connection.fetchval(query)
                samples.append(round((time.perf_counter() - started) * 1000, 3))
            latency[label] = distribution(samples)
        transaction_times = []
        for _ in range(10):
            started = time.perf_counter()
            async with connection.transaction(readonly=True):
                assert await connection.fetchval("show transaction_read_only") == "on"
                assert await connection.fetchval("select count(*) from public.languages") == 6
            transaction_times.append(round((time.perf_counter() - started) * 1000, 3))
        latency["read_only_transaction"] = distribution(transaction_times)
        latency["connection"] = distribution(connect_times)
        async with connection.transaction(readonly=True):
            catalog = json.loads(await connection.fetchval(CATALOG))
            for function in catalog.get("functions", {}).values():
                body = function.pop("body")
                function["body_sha256"] = hashlib.sha256(body.encode()).hexdigest()
            extra = json.loads(await connection.fetchval("""select jsonb_build_object(
              'extensions',(select jsonb_agg(jsonb_build_object('name',extname,'version',extversion,'schema',n.nspname)) from pg_extension e join pg_namespace n on n.oid=e.extnamespace),
              'views',(select coalesce(jsonb_agg(jsonb_build_object('name',c.relname,'kind',c.relkind,'options',c.reloptions)), '[]'::jsonb) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind in ('v','m')),
              'sequences',(select coalesce(jsonb_agg(sequencename),'[]'::jsonb) from pg_sequences where schemaname='public'),
              'table_grants',(select coalesce(jsonb_agg(jsonb_build_object('table',table_name,'role',grantee,'privilege',privilege_type)),'[]'::jsonb) from information_schema.role_table_grants where table_schema='public'),
              'schema_grants',(select jsonb_agg(jsonb_build_object('role',role_name,'usage',has_schema_privilege(role_name,'public','USAGE'),'create',has_schema_privilege(role_name,'public','CREATE'))) from (values('anon'),('authenticated'),('service_role')) r(role_name)),
              'function_grants',(select coalesce(jsonb_agg(jsonb_build_object('function',p.proname,'signature',pg_get_function_identity_arguments(p.oid),'role',r.role_name,'security_definer',p.prosecdef,'extension_owned',exists(select 1 from pg_depend d where d.classid='pg_proc'::regclass and d.objid=p.oid and d.deptype='e'))),'[]'::jsonb) from pg_proc p join pg_namespace n on n.oid=p.pronamespace cross join (values('anon'),('authenticated'))r(role_name) where n.nspname='public' and has_function_privilege(r.role_name,p.oid,'EXECUTE')),
              'roles',(select jsonb_agg(jsonb_build_object('name',rolname,'superuser',rolsuper,'login',rolcanlogin,'bypassrls',rolbypassrls,'inherit',rolinherit)) from pg_roles),
              'memberships',(select jsonb_agg(jsonb_build_object('role',r.rolname,'member',m.rolname,'admin_option',a.admin_option)) from pg_auth_members a join pg_roles r on r.oid=a.roleid join pg_roles m on m.oid=a.member),
              'default_privileges',(select jsonb_agg(jsonb_build_object('owner',pg_get_userbyid(d.defaclrole),'schema',n.nspname,'object_type',d.defaclobjtype,'acl',d.defaclacl)) from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace),
              'realtime',(select jsonb_agg(jsonb_build_object('publication',pubname,'schema',schemaname,'table',tablename)) from pg_publication_tables),
              'buckets',(select coalesce(jsonb_agg(jsonb_build_object('name',name,'public',public)),'[]'::jsonb) from storage.buckets),
              'storage_policies',(select coalesce(jsonb_agg(jsonb_build_object('table',tablename,'policy',policyname,'cmd',cmd,'roles',roles,'using',qual,'check',with_check)),'[]'::jsonb) from pg_policies where schemaname='storage'),
              'alembic',(select coalesce(jsonb_agg(version_num),'[]'::jsonb) from public.alembic_version),
              'extra_booking_columns',(select jsonb_agg(jsonb_build_object('name',column_name,'type',data_type,'nullable',is_nullable)) from information_schema.columns where table_schema='public' and table_name='bookings' and column_name in ('cancellation_reason_code','cancellation_reason_text')),
              'cron_installed',exists(select 1 from pg_extension where extname='pg_cron')
            )"""))
        evidence = {"destination": REF, "pooler": {"host": HOST, "port": 5432,
            "database": "postgres", "username": f"postgres.{REF}",
            "scope_verification": "Exact project-scoped pooler username; management lookup independently verifies Mumbai ref/region. Shared host is not project-exclusive."},
            "identity": identity, "tls": {"ca_required": True, "hostname_required": True,
                "x509_strict": False, "exception": "Test-only compatibility for missing intermediate Key Usage",
                "upstream_pg_stat_ssl": dict(upstream_tls) if upstream_tls else None},
            "latency": latency, "catalog": catalog, "additional_inventory": extra,
            "remote_schema_changed": False, "alembic_stamped": False}
        output = ROOT / "backend/migrations/reviews/migration-mumbai-completion-audit-2026-10-15.json"
        output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"identity": identity,"tls": evidence["tls"],
            "latency": {key: {k: v for k,v in val.items() if k != 'samples_ms'} for key,val in latency.items()},
            "catalog_counts": {key: len(val or {}) for key,val in catalog.items()},
            "alembic": extra['alembic'], "artifact": output.name}, indent=2))
    finally:
        await connection.close()


if __name__ == '__main__':
    try:
        asyncio.run(audit())
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
