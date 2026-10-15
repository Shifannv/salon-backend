"""Mumbai-only rollback runtime tests. Never execute migration/DDL/grant SQL.

Synthetic Auth rows are inserted through SQL inside the outer rollback transaction;
no Auth HTTP session/mail creation occurs. API actor extraction is explicitly injected,
so these checks exercise business authorization, not JWT/Google/email verification.
"""

import asyncio
import contextlib
import hashlib
import io
import json
import logging
import re
import ssl
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from urllib.parse import unquote
from uuid import uuid4

import httpx
from backend.scripts.migrations.migration_mumbai_staging_20261015 import (
    BASE,
    CA_URL,
    HOST,
    REF,
    ROOT,
    config_values,
)
from sqlalchemy import URL, event, text

ACTORS = {role: str(uuid4()) for role in ("customer", "owner", "outsider")}
RESULTS = []
ERRORS = []
CATALOG_BEFORE = None


def record(check, status="passed", **facts):
    RESULTS.append({"check": check, "status": status, **facts})


async def metadata(connection):
    from backend.scripts.migrations.migration_mumbai_reference_20261015 import CATALOG

    catalog = (await connection.execute(text(CATALOG))).scalar_one()
    if isinstance(catalog, str):
        catalog = json.loads(catalog)
    acls = (await connection.execute(text("""SELECT jsonb_build_object(
      'relations',(SELECT jsonb_agg(jsonb_build_object('name',c.relname,'acl',c.relacl) ORDER BY c.relname)
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'),
      'functions',(SELECT jsonb_agg(jsonb_build_object('signature',p.oid::regprocedure::text,'acl',p.proacl) ORDER BY p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'),
      'columns',(SELECT jsonb_agg(jsonb_build_object('table',c.relname,'column',a.attname,'acl',a.attacl) ORDER BY c.relname,a.attnum)
        FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND a.attnum>0 AND NOT a.attisdropped),
      'defaults',(SELECT jsonb_agg(jsonb_build_object('creator',d.defaclrole,'schema',d.defaclnamespace,'kind',d.defaclobjtype,'acl',d.defaclacl) ORDER BY d.oid) FROM pg_default_acl d),
      'memberships',(SELECT jsonb_agg(jsonb_build_object('role',roleid,'member',member,'grantor',grantor,'admin',admin_option,'inherit',inherit_option,'set',set_option) ORDER BY roleid,member,grantor) FROM pg_auth_members)
    )"""))).scalar_one()
    names = sorted(catalog["tables"])
    assert all(re.fullmatch(r"[a-z_]+", name) for name in names)
    pairs = [f"'{name}',(SELECT count(*) FROM public.{name})" for name in names]
    pairs += ["'auth_users',(SELECT count(*) FROM auth.users)",
              "'auth_sessions',(SELECT count(*) FROM auth.sessions)"]
    counts = (await connection.execute(text("SELECT jsonb_build_object(" + ",".join(pairs) + ")"))).scalar_one()
    return catalog, acls, counts


async def setup(connection):
    results = []
    for role, actor in ACTORS.items():
        # No real mailbox, password, session, identity-provider call or outbound email.
        await connection.execute(text("""INSERT INTO auth.users
            (id,email,aud,role,raw_app_meta_data,raw_user_meta_data)
            VALUES (:id,:email,'authenticated','authenticated',cast(:app as jsonb),'{}'::jsonb)"""),
            {"id": actor, "email": f"runtime-{actor}@example.com",
             "app": json.dumps({"role": "customer" if role == "outsider" else role})})
        actual = (await connection.execute(text("SELECT role::text FROM public.profiles WHERE id=:id"),
                                          {"id": actor})).scalar_one()
        assert actual == ("customer" if role == "outsider" else role)
    record("signup_trigger_synthetic_sql_insert", created_profiles=3, auth_http_signup_tested=False)
    return results


async def probe(connection, ids, payload, booking_id, *, fastapi_only=False):
    # Current no-grant posture: denied client reads are expected; row-level ownership
    # cannot be reached without table/helper access and is not falsely called passed.
    for role in ("customer", "owner"):
        savepoint = await connection.begin_nested()
        try:
            await connection.execute(text("SELECT set_config('request.jwt.claim.sub',:actor,true),set_config('request.jwt.claims',:claims,true)"),
                {"actor": ACTORS[role], "claims": json.dumps({"sub": ACTORS[role]})})
            await connection.execute(text("SET LOCAL ROLE authenticated"))
            await connection.execute(text("SELECT count(*) FROM public.bookings WHERE id=:id"), {"id": booking_id})
            raise AssertionError("Unexpected direct-client read access")
        except Exception as exc:
            state = getattr(getattr(exc, "orig", exc), "sqlstate", None)
            if state != "42501":
                raise
            ERRORS.append({"test": f"{role}_direct_booking_read", "sqlstate": state,
                           "expected": True, "meaning": "insufficient_privilege"})
            record(f"{role}_direct_client_denied", expected_sqlstate=state)
        finally:
            await savepoint.rollback()
        record(f"{role}_scoped_RLS_row_filter", "not_applicable" if fastapi_only else "blocked",
               reason="FastAPI-only architecture; direct client 42501 is expected. No grants added."
               if fastapi_only else "Table access denied; no temporary grants authorized. API ownership tested separately.")
    # Real SET ROLE service_role (not postgres masquerading as a server RPC test).
    savepoint = await connection.begin_nested()
    try:
        await connection.execute(text("SELECT set_config('request.jwt.claim.sub',:actor,true),set_config('request.jwt.claims',:claims,true)"),
            {"actor": ACTORS["outsider"], "claims": json.dumps({"sub": ACTORS["outsider"]})})
        await connection.execute(text("SET LOCAL ROLE service_role"))
        assert (await connection.execute(text("SELECT current_user"))).scalar_one() == "service_role"
        slots = (await connection.execute(text("SELECT count(*) FROM public.get_available_slots(:staff,cast(:day as date),30)"),
                   {"staff": ids["staff"], "day": datetime.fromisoformat(payload["start_datetime"]).date()})).scalar_one()
        assert slots > 0
        start = datetime.fromisoformat(payload["start_datetime"]) + timedelta(days=1)
        created = (await connection.execute(text("""SELECT public.create_booking(
            cast(:salon as uuid),cast(:staff as uuid),ARRAY[cast(:service as uuid)],
            cast(:start as timestamptz),'Synthetic runtime customer',NULL,
            'app'::public.booking_source,NULL)"""), {**ids, "start": start})).scalar_one()
        assert created is not None
        record("service_role_availability", slot_count=slots)
        record("service_role_create_booking", role_verified=True)
    finally:
        # This RPC fixture is unnecessary for later API tests; discard its savepoint now.
        await savepoint.rollback()
    return []


async def main(*, probe_hook=None, fastapi_only=False):
    logging.disable(logging.CRITICAL)
    values, parts = config_values()  # Mumbai target guards; never print values.
    async with httpx.AsyncClient(timeout=20) as web:
        ca = await web.get(CA_URL)
        ca.raise_for_status()
    tls = ssl.create_default_context()
    tls.load_verify_locations(cadata=ca.text)
    tls.verify_flags &= ~ssl.VERIFY_X509_STRICT
    assert tls.verify_mode == ssl.CERT_REQUIRED and tls.check_hostname
    sys.path.insert(0, str(ROOT / "backend"))
    from app.core import config

    target = URL.create("postgresql+asyncpg", username=f"postgres.{REF}",
        password=unquote(parts.password or ""), host=HOST, port=5432, database="postgres")
    config.settings = config.Settings(_env_file=None, environment="staging",
        database_url=target.render_as_string(hide_password=False), supabase_url=BASE,
        supabase_jwks_url=BASE + "/auth/v1/.well-known/jwks.json",
        supabase_anon_key=values["SUPABASE_ANON_KEY"],
        supabase_service_role_key=values["SUPABASE_SERVICE_ROLE_KEY"],
        payment_provider="none", subscription_provider="none", cashfree_enabled=False,
        redis_url=None, sentry_dsn=None, firebase_credentials_json=None, resend_api_key=None,
        r2_access_key_id=None)
    from app.infrastructure.db import session as db

    @event.listens_for(db._pool_engine.sync_engine, "do_connect")
    def verified_tls(dialect, connection_record, args, kwargs):
        kwargs["ssl"] = tls

    @event.listens_for(db._pool_engine.sync_engine, "before_cursor_execute")
    def prohibit_schema_or_grant_sql(conn, cursor, statement, parameters, context, executemany):
        if re.match(r"\s*(?:CREATE|ALTER|DROP|GRANT|REVOKE|TRUNCATE|COMMENT)\b", statement, re.IGNORECASE):
            raise RuntimeError("Forbidden schema/privilege SQL blocked before execution")

    from backend.scripts.migrations.evidence.migration_mumbai_booking_20261015 import (
        rollback_checks,
    )
    from fastapi import Depends, Request

    from app.api.deps import get_current_actor
    from app.infrastructure.db.repositories.profile_repository import (
        SQLProfileRepository,
    )
    from app.main import app

    actor_session_dependency = Depends(db.get_session)

    async def actor_override(request: Request, session=actor_session_dependency):
        role = request.headers.get("x-runtime-role")
        if role not in ACTORS:
            from app.core.exceptions import UnauthorizedError
            raise UnauthorizedError("Synthetic runtime actor required")
        request.state.verified_auth_claims = {"sub": ACTORS[role]}
        profile = await SQLProfileRepository(session).get_by_id(ACTORS[role])
        assert profile is not None
        return profile

    # Local imports used in annotations are resolved explicitly for FastAPI.
    actor_override.__annotations__["request"] = Request
    app.dependency_overrides[get_current_actor] = actor_override
    before = None
    try:
        async with db.engine.connect() as connection:  # noqa: SIM117 -- make transaction boundary explicit.
            async with connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                before = await metadata(connection)
                assert (await connection.execute(text("SELECT current_database()"))).scalar_one() == "postgres"
                for name in ("cancellation_reason_code", "cancellation_reason_text"):
                    column = before[0]["columns"][f"bookings.{name}"]
                    assert column == {"type": "text", "default": None, "identity": "", "not_null": False, "generated": ""}
                record("schema_only_target_readonly_assertions", extra_columns_preserved=True)
                function_configs = {k: v["config"] for k, v in before[0]["functions"].items()}
                assert function_configs["handle_new_user()"] == ["search_path=public"]
                promotion = next(v for k, v in function_configs.items() if k.startswith("is_subscription_promotion_active("))
                assert promotion == ["search_path=public"]
                record("function_search_path_verification", function_count=len(function_configs))
                unsafe_definers = [k for k, v in before[0]["functions"].items()
                                   if v["security_definer"] and not v["config"]]
                assert not unsafe_definers
                record("security_definer_fixed_configuration", unsafe_count=len(unsafe_definers),
                       security_definer_count=sum(v["security_definer"] for v in before[0]["functions"].values()))
                # Effective ACL checks as the actual managed roles, not inferred ACL text.
                privileges = (await connection.execute(text("""SELECT
                  (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                   CROSS JOIN (VALUES('anon'),('authenticated'))r(role)
                   CROSS JOIN (VALUES('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),('TRIGGER'),('MAINTAIN'))v(privilege)
                   WHERE n.nspname='public' AND c.relkind='r' AND has_table_privilege(r.role,c.oid,v.privilege)) AS client_table_rights,
                  (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                   CROSS JOIN (VALUES('anon'),('authenticated'))r(role) WHERE n.nspname='public'
                   AND NOT EXISTS(SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e')
                   AND has_function_privilege(r.role,p.oid,'EXECUTE')) AS client_app_execute,
                  has_function_privilege('service_role','public.create_booking(uuid,uuid,uuid[],timestamptz,text,text,public.booking_source,text)','EXECUTE') AS service_booking,
                  has_function_privilege('service_role','public.get_available_slots(uuid,date,integer)','EXECUTE') AS service_slots"""))).mappings().one()
                assert privileges["client_table_rights"] == privileges["client_app_execute"] == 0
                assert privileges["service_booking"] and privileges["service_slots"]
                record("security_target_effective_ACL_readonly_assertions", **dict(privileges))
                versions = (await connection.execute(text("SELECT count(*) FROM public.alembic_version"))).scalar_one()
                assert versions == 0
                record("alembic_history_unchanged_empty", rows=versions)
        headers = {role: {"x-runtime-role": role} for role in ("customer", "owner")}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                   base_url="http://mumbai-rollback-runtime") as api:
            async def selected_probe(connection, ids, payload, booking_id):
                await probe(connection, ids, payload, booking_id, fastapi_only=fastapi_only)
                if probe_hook:
                    await probe_hook(api, connection, ids, payload, booking_id, ACTORS)
                return []

            with patch("app.infrastructure.push.outbox_worker.enqueue_and_deliver_notification", new=AsyncMock()):
                business = await rollback_checks(api, app, db, headers, completion=True,
                    actors=ACTORS, runtime_setup=setup, runtime_probe=selected_probe)
                RESULTS.extend(business)
    finally:
        app.dependency_overrides.pop(get_current_actor, None)
        async with db.engine.connect() as connection:  # noqa: SIM117 -- make transaction boundary explicit.
            async with connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                after = await metadata(connection)
                if before:
                    assert before == after
                    record("schema_function_ACL_memberships_defaults_and_all_table_counts_unchanged")
                for table in ("auth.users", "public.profiles"):
                    remaining = (await connection.execute(text(f"SELECT count(*) FROM {table} WHERE id=ANY(cast(:ids as uuid[]))"),
                                      {"ids": list(ACTORS.values())})).scalar_one()
                    assert remaining == 0
                record("transaction_rollback_synthetic_users_and_profiles", remaining=0)
                CATALOG_BEFORE_VALUE = before[0] if before else None
                global CATALOG_BEFORE
                CATALOG_BEFORE = CATALOG_BEFORE_VALUE
        await db.engine.dispose()


if __name__ == "__main__":
    captured = io.StringIO()
    failure = None
    with contextlib.redirect_stdout(captured):
        try:
            asyncio.run(main())
        except Exception as exc:
            failure = type(exc).__name__
            state = getattr(getattr(exc, "orig", exc), "sqlstate", None)
            ERRORS.append({"test": "runtime_runner", "type": failure, "sqlstate": state,
                           "expected": False})
    if failure:
        for line in captured.getvalue().splitlines():
            try:
                partial = json.loads(line)
            except ValueError:
                continue
            for key in ("rollback_booking_results_before_failure", "completion_business_results_before_failure"):
                RESULTS.extend(partial.get(key, []))
    evidence = {"destination": REF, "results": RESULTS,
        "sql_errors": [e for e in ERRORS if e.get("sqlstate")],
        "runtime_failures": [e for e in ERRORS if not e.get("sqlstate")],
        "failure_type": failure, "migrations_executed": False, "schema_or_grant_sql_executed": False,
        "stamp_executed": False, "auth_http_mutations": False,
        "api_identity": "injected synthetic actor; JWT verification not tested",
        "api_base": "http://mumbai-rollback-runtime (in-process ASGI)",
        "TLS": "CA/hostname verified; previously disclosed strict-X509 compatibility exception retained"}
    (ROOT / "backend/migrations/reviews/migration-mumbai-runtime-results-2026-10-15.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    if CATALOG_BEFORE:
        safe_catalog = json.loads(json.dumps(CATALOG_BEFORE))
        for func in safe_catalog["functions"].values():
            body = func.pop("body")
            func["body_sha256"] = hashlib.sha256(body.encode()).hexdigest()
        (ROOT / "backend/migrations/reviews/migration-mumbai-runtime-catalog-2026-10-15.json").write_text(json.dumps(safe_catalog, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    raise SystemExit(1 if failure else 0)
