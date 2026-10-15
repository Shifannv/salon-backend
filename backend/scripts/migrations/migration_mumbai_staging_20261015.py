"""Mumbai-only, in-process API smoke checks; secrets are never printed or saved."""

import asyncio
import json
import logging
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from sqlalchemy import URL, event

ROOT = Path(__file__).resolve().parents[4]
REF = "wqjlgpnbiapcrlkxumcp"
BASE = f"https://{REF}.supabase.co"
HOST = "aws-0-ap-south-1.pooler.supabase.com"
CA_URL = "https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt"
ACCOUNTS = {
    "customer": "7alonbooking+mumbai-customer-20261015@gmail.com",
    "owner": "7alonbooking+mumbai-owner-20261015@gmail.com",
}


def config_values():
    allowed = {"SUPABASE_URL", "DATABASE_URL", "SUPABASE_ANON_KEY",
               "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY"}
    values = {}
    for line in (ROOT / "backend/.env").read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() in allowed:
            values[key.strip()] = value.strip().strip('"').strip("'")
    if values.get("SUPABASE_URL", "").rstrip("/") != BASE:
        raise RuntimeError("Local Auth target is not Mumbai")
    parts = urlsplit(values["DATABASE_URL"])
    if REF not in (parts.hostname or "") and parts.username != f"postgres.{REF}":
        raise RuntimeError("Local database target is not Mumbai")
    return values, parts


async def run(*, api_benchmarks=False):
    logging.disable(logging.CRITICAL)
    values, parts = config_values()
    ca = await asyncio.to_thread(httpx.get, CA_URL, timeout=15)
    ca.raise_for_status()
    context = ssl.create_default_context()
    context.load_verify_locations(cadata=ca.text)
    # Explicit diagnostic compatibility exception for Supabase's intermediate CA.
    # CA verification and hostname verification remain mandatory.
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    sys.path.insert(0, str(ROOT / "backend"))
    from app.core import config

    url = URL.create("postgresql+asyncpg", username=f"postgres.{REF}",
                     password=unquote(parts.password or ""), host=HOST,
                     port=5432, database="postgres")
    config.settings = config.Settings(
        _env_file=None, environment="staging",
        database_url=url.render_as_string(hide_password=False),
        supabase_url=BASE, supabase_jwks_url=BASE + "/auth/v1/.well-known/jwks.json",
        supabase_anon_key=values["SUPABASE_ANON_KEY"],
        supabase_service_role_key=values["SUPABASE_SERVICE_ROLE_KEY"],
        payment_provider="none", subscription_provider="none", cashfree_enabled=False,
        redis_url=None, sentry_dsn=None, firebase_credentials_json=None,
        resend_api_key=None, r2_access_key_id=None,
    )
    from app.infrastructure.db import session

    @event.listens_for(session._pool_engine.sync_engine, "do_connect")
    def require_verified_tls(dialect, connection_record, args, kwargs):
        kwargs["ssl"] = context

    from app.main import app

    results = []
    headers_by_role = {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                 base_url="http://mumbai-local-test") as api:
        for path in ("/health", "/health/db", "/health/redis", "/health/ready", "/v1/salons"):
            started = time.perf_counter()
            response = await api.get(path)
            results.append({"path": path, "status": response.status_code,
                            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)})
            if response.status_code != 200:
                results[-1]["error_code"] = response.json().get("error", {}).get("code")
                print(json.dumps({"results": results, "stopped_at_first_failure": True}, indent=2))
                await session.engine.dispose()
                return
        async with httpx.AsyncClient(base_url=BASE, timeout=20) as auth:
            for role, email in ACCOUNTS.items():
                generated = await auth.post("/auth/v1/admin/generate_link",
                    headers={"apikey": values["SUPABASE_SECRET_KEY"]},
                    json={"type": "magiclink", "email": email})
                if generated.status_code != 200:
                    results.append({"role": role, "generate_link_status": generated.status_code})
                    break
                data = generated.json()
                hashed = data.get("hashed_token") or data.get("properties", {}).get("hashed_token")
                verified = await auth.post("/auth/v1/verify",
                    headers={"apikey": values["SUPABASE_PUBLISHABLE_KEY"]},
                    json={"type": "magiclink", "token_hash": hashed})
                if verified.status_code != 200:
                    results.append({"role": role, "verify_status": verified.status_code})
                    break
                token = verified.json()["access_token"]
                headers = {"Authorization": "Bearer " + token}
                headers_by_role[role] = headers
                for path in ("/v1/auth/me", "/v1/bookings"):
                    started = time.perf_counter()
                    response = await api.get(path, headers=headers)
                    item = {"role": role, "path": path, "status": response.status_code,
                            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}
                    if path.endswith("/me") and response.status_code == 200:
                        item["resolved_profile_role"] = response.json().get("role")
                    results.append(item)
                    expected = 403 if role == "owner" and path == "/v1/bookings" else 200
                    item["expected_status"] = expected
                    if response.status_code != expected:
                        break
            try:
                if len(headers_by_role) == 2:
                    from migration_mumbai_booking_20261015 import rollback_checks
                    results.extend(await rollback_checks(api, app, session, headers_by_role))
            finally:
                for headers in headers_by_role.values():
                    await auth.post("/auth/v1/logout?scope=global", headers={
                        "apikey": values["SUPABASE_PUBLISHABLE_KEY"], **headers})
        response = await api.get("/v1/auth/me", headers={"Authorization": "Bearer invalid"})
        results.append({"path": "/v1/auth/me", "invalid_token_status": response.status_code})
        if api_benchmarks:
            import statistics
            for path in ("/health/db", "/v1/salons"):
                samples = []
                for _ in range(10):
                    started = time.perf_counter()
                    response = await api.get(path)
                    assert response.status_code == 200
                    samples.append(round((time.perf_counter() - started)*1000, 3))
                results.append({"check": "ten_request_API_latency", "path": path,
                                "samples_ms": samples, "median_ms": round(statistics.median(samples), 3),
                                "p95_nearest_rank_ms": max(samples), "transport": "in-process ASGI"})
    await session.engine.dispose()
    print(json.dumps({"results": results, "payments_enabled": False,
                      "test_transport": "in-process ASGI; real Mumbai Auth and database"}, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as exc:  # noqa: BLE001 -- CLI boundary must redact remote credentials.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
