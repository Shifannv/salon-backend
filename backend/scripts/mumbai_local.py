"""Guarded Mumbai-only local staging entry point. Never runs migrations.

Prepare explicitly from a verified credential source, then serve/probe using only
the ignored .env.mumbai-local file. Output contains targets/measurements, not secrets.
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parents[1]
REF = "wqjlgpnbiapcrlkxumcp"
BASE = f"https://{REF}.supabase.co"
STAGE = BACKEND / ".env.mumbai-local"
ARTIFACTS = BACKEND / ".artifacts" / "mumbai-refresh"
REDIS = "redis://127.0.0.1:16391/0"
CA_URL = "https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt"


def validate(values):
    assert values.get("SUPABASE_URL", "").rstrip("/") == BASE, "Auth target mismatch"
    assert values.get("SUPABASE_JWKS_URL", "").rstrip("/") == BASE + "/auth/v1/.well-known/jwks.json", "JWKS target mismatch"
    db = urlsplit(values.get("DATABASE_URL", ""))
    direct = db.hostname == f"db.{REF}.supabase.co" and db.username == "postgres"
    pooled = db.hostname in {"aws-0-ap-south-1.pooler.supabase.com", "aws-1-ap-south-1.pooler.supabase.com"} and unquote(db.username or "") == f"postgres.{REF}"
    assert direct or pooled, "Database target mismatch"
    key = values.get("SUPABASE_SERVICE_ROLE_KEY", "")
    payload = key.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert claims.get("ref") == REF and claims.get("role") == "service_role", "Service key claims mismatch"
    return db


def prepare(source):
    source = Path(source).resolve()
    assert source != STAGE, "Source must differ from staging output"
    values = dotenv_values(source, interpolate=False)
    validate(values)
    assert not STAGE.exists(), "Staging file exists; inspect it instead of overwriting"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    ca = httpx.get(CA_URL, timeout=20)
    ca.raise_for_status()
    ca_path = ARTIFACTS / "supabase-ca.pem"
    ca_path.write_text(ca.text, encoding="utf-8")
    ssl.create_default_context(cafile=str(ca_path))
    selected = {key: values[key] for key in (
        "DATABASE_URL", "SUPABASE_URL", "SUPABASE_ANON_KEY",
        "SUPABASE_JWKS_URL", "SUPABASE_SERVICE_ROLE_KEY",
    )}
    selected.update({
        "ENVIRONMENT": "staging", "PORT": "8056", "REDIS_URL": REDIS,
        "DB_SSL_CA_FILE": str(ca_path), "SUPABASE_JWT_AUDIENCE": "authenticated",
        "PAYMENT_PROVIDER": "none", "SUBSCRIPTION_PROVIDER": "none",
        "CASHFREE_ENABLED": "false", "PAYMENT_ALLOW_LIVE": "false",
        "SUBSCRIPTION_ALLOW_LIVE": "false", "SENTRY_DSN": "",
        "RESEND_API_KEY": "", "FIREBASE_CREDENTIALS_JSON": "",
        "R2_ACCESS_KEY_ID": "", "R2_SECRET_ACCESS_KEY": "",
        "BACKEND_CORS_ORIGINS": '["http://localhost:3000","http://localhost:8081","http://localhost:8082","http://127.0.0.1:8081","http://127.0.0.1:8082"]',
    })
    STAGE.write_text("# Private Mumbai local staging; never commit.\n" + "\n".join(
        f"{key}={json.dumps(value)}" for key, value in selected.items()
    ) + "\n", encoding="utf-8")
    print(json.dumps({"prepared": True, "file": STAGE.name, "project": REF}))


def bind():
    assert STAGE.is_file(), "Prepare explicit staging configuration first"
    values = dotenv_values(STAGE, interpolate=False)
    db = validate(values)
    from sqlalchemy.engine import make_url
    values["DATABASE_URL"] = make_url(values["DATABASE_URL"]).set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    assert values.get("REDIS_URL") == REDIS, "Redis must be the isolated loopback instance"
    assert values.get("ENVIRONMENT") == "staging", "Environment mismatch"
    assert values.get("PAYMENT_PROVIDER") == values.get("SUBSCRIPTION_PROVIDER") == "none", "Providers must be disabled"
    # Explicit file values win over inherited process configuration.
    os.environ.update({key: value for key, value in values.items() if value is not None})
    os.environ["SALON_ENV_FILE"] = str(STAGE)
    os.environ["DB_SSL_STRICT"] = "false"
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    return {"project": REF, "database_host": db.hostname,
            "auth_host": urlsplit(BASE).hostname, "jwks_host": urlsplit(BASE).hostname,
            "redis_host": "127.0.0.1", "redis_port": 16391,
            "env_file": STAGE.name, "api": "http://127.0.0.1:8056",
            "tls": "verify-full; published Supabase CA; legacy CA keyUsage compatibility"}


def percentiles(samples):
    samples = sorted(samples)
    return {f"p{p}": round(samples[min(len(samples) - 1, int((len(samples)-1)*p/100))], 3)
            for p in (50, 95, 99)}


async def probe(targets, samples):
    from sqlalchemy import text

    from app.infrastructure.db.session import AsyncSessionLocal, engine
    from app.main import app, lifespan

    result = {"targets": targets, "samples": samples, "checks": {}}
    async with httpx.AsyncClient(timeout=20) as remote:
        jwks = await remote.get(BASE + "/auth/v1/.well-known/jwks.json")
        result["checks"]["jwks_https"] = jwks.status_code == 200 and bool(jwks.json().get("keys"))
        # A missing synthetic UUID establishes Admin authorization without reading real users.
        admin = await remote.get(BASE + "/auth/v1/admin/users/00000000-0000-4000-8000-000000000000",
            headers={"apikey": os.environ["SUPABASE_ANON_KEY"],
                     "Authorization": "Bearer " + os.environ["SUPABASE_SERVICE_ROLE_KEY"]})
        result["checks"]["service_key_authorized"] = admin.status_code == 404 and admin.json().get("error_code", admin.json().get("code")) == "user_not_found"
        result["checks"]["service_key_probe_status"] = admin.status_code
        result["checks"]["service_key_probe_code"] = admin.json().get("error_code", admin.json().get("code"))
    async with lifespan(app):
        async with AsyncSessionLocal() as session:
            tls = (await session.execute(text("select ssl from pg_stat_ssl where pid = pg_backend_pid()"))).scalar_one()
            result["checks"]["pooler_database_hop_ssl"] = bool(tls)
            raw = await (await session.connection()).get_raw_connection()
            tls_socket = raw.driver_connection._transport.get_extra_info("ssl_object")
            result["checks"]["database_tls"] = tls_socket is not None
            result["checks"]["database_tls_protocol"] = tls_socket.version() if tls_socket else None
            result["checks"]["alembic_history_rows"] = (await session.execute(text("select count(*) from public.alembic_version"))).scalar_one()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=targets["api"]) as client:
            for path in ("/health", "/health/db", "/health/redis", "/health/ready"):
                timings = []
                for _ in range(samples):
                    started = time.perf_counter()
                    response = await client.get(path, headers={"X-Request-ID": "mumbai-refresh-probe"})
                    timings.append((time.perf_counter() - started) * 1000)
                    assert response.status_code == 200, "Health probe failed"
                    assert response.headers.get("x-request-id") == "mumbai-refresh-probe", "Request ID missing"
                    assert "server-timing" in response.headers, "Timing header missing"
                result["checks"][path] = {"status": response.json(), "latency_ms": percentiles(timings)}
    await engine.dispose()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "configuration-probe.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    assert result["checks"]["database_tls"] and result["checks"]["jwks_https"] and result["checks"]["service_key_authorized"], "Target/TLS/Auth check failed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-from")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--pooler", action="store_true", help="Use the Mumbai session pooler when direct IPv6 DNS is unavailable")
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()
    try:
        if args.prepare_from:
            prepare(args.prepare_from)
            return
        targets = bind()
        if args.pooler:
            from sqlalchemy.engine import make_url
            os.environ["DATABASE_URL"] = make_url(os.environ["DATABASE_URL"]).set(
                host="aws-0-ap-south-1.pooler.supabase.com", port=5432,
                username=f"postgres.{REF}",
            ).render_as_string(hide_password=False)
            targets["database_host"] = "aws-0-ap-south-1.pooler.supabase.com"
        if args.probe:
            # Silence third-party exception logging: report only exception types below.
            logging.disable(logging.CRITICAL)
            asyncio.run(probe(targets, max(1, min(args.samples, 100))))
        else:
            import uvicorn
            print(json.dumps({"targets": targets}))
            uvicorn.run("app.main:app", host="127.0.0.1", port=8056, access_log=False)
    except Exception as error:
        print(json.dumps({"status": "blocked", "error_type": type(error).__name__,
                          "missing_module": getattr(error, "name", None),
                          "tls_verify_code": getattr(error, "verify_code", None),
                          "tls_verify_message": getattr(error, "verify_message", None),
                          "check": str(error) if isinstance(error, AssertionError) else None}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
