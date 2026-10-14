"""Disposable local API with an explicit Supabase Auth test double for device checks.

This DOES NOT test real Supabase Auth/SMTP. It signs ephemeral test JWTs against local
JWKS; the normal FastAPI verifier and database role/ownership checks still run.
Run from repo root (no .env there), only after an explicit disposable DB preparation.
"""

import argparse
import asyncio
import base64
import json
import os
import time
from pathlib import Path
from uuid import uuid4

# Never inherit service credentials for this local-only process.
os.environ.update(ENVIRONMENT="test", PAYMENT_PROVIDER="none", SUBSCRIPTION_PROVIDER="none",
    CASHFREE_ENABLED="false", RESEND_API_KEY="", SENTRY_DSN="", FIREBASE_CREDENTIALS_JSON="",
    SUPABASE_SERVICE_ROLE_KEY="", SUPABASE_ANON_KEY="local-test-public-key",
    SUPABASE_URL="http://127.0.0.1:8050", SUPABASE_JWKS_URL="http://127.0.0.1:8050/auth/v1/.well-known/jwks.json",
    REDIS_URL="redis://127.0.0.1:56389/0")

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jose import jwt

MANIFEST = Path(__file__).parents[2] / ".artifacts/local-fixtures.json"


def fixture_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


async def prepare(admin_url):
    os.environ["MIGRATION_TEST_DB"] = admin_url
    from tests.integration.test_checkout_safety_sql import SafetyEnv
    from tests.integration.test_payment_ledger_sql import _build
    database = "salon_local_test_" + uuid4().hex[:12]
    await _build(database)
    from sqlalchemy.engine import make_url
    url=make_url(admin_url).set(database=database,drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    env=SafetyEnv(url)
    fixture=await env.seed()
    # Known test identities, never real customer data.
    await env.sql("update profiles set email='customer@example.com',full_name='Test Customer',phone='+919000000001',phone_verified=true where id=:id",id=fixture["customer"])
    await env.sql("update profiles set email='owner@example.com',full_name='Test Owner',phone='+919000000002',phone_verified=true where id=:id",id=fixture["owner"])
    await env.engine.dispose()
    # This explicit --prepare operation replaces ONLY the dedicated localhost
    # synthetic fixture. Its separate Redis container must not retain old IDs.
    import redis.asyncio as redis
    cache=redis.from_url("redis://127.0.0.1:56389/0")
    await cache.flushdb()
    await cache.aclose()
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps({**fixture,"start":fixture["start"].isoformat(),"database_url":url},indent=2),encoding="utf-8")
    print("Prepared disposable local fixture database " + database)


def app_factory():
    f=fixture_manifest()
    # Allow only the dedicated local test database. Never runtime .env/production.
    from sqlalchemy.engine import make_url
    url=make_url(f["database_url"])
    assert url.host in {"localhost","127.0.0.1"} and url.database.startswith("salon_local_test_")
    os.environ["DATABASE_URL"]=f["database_url"]
    from app.api import deps
    from app.main import create_app
    app=create_app()
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    numbers=key.public_key().public_numbers()
    def encode_number(n):
        return base64.urlsafe_b64encode(n.to_bytes((n.bit_length()+7)//8,"big")).rstrip(b"=").decode()
    jwks={"keys":[{"kty":"RSA","kid":"local-test","use":"sig","alg":"RS256","n":encode_number(numbers.n),"e":encode_number(numbers.e)}]}
    deps._jwt_verifier._jwks=jwks
    deps._jwt_verifier._jwks_fetched_at=time.monotonic()
    router=APIRouter(prefix="/auth/v1")

    def user(uid,email):
        return {"id":uid,"aud":"authenticated","role":"authenticated","email":email,
                "email_confirmed_at":"2026-01-01T00:00:00Z","app_metadata":{"provider":"email","providers":["email"]},
                "user_metadata":{"full_name":"Test Owner" if uid==f["owner"] else "Test Customer"},
                "created_at":"2026-01-01T00:00:00Z"}

    def session(uid,email):
        claims={"sub":uid,"aud":"authenticated","iss":"http://127.0.0.1:8050/auth/v1","iat":int(time.time()),
                "exp":int(time.time())+3600,"email":email,"role":"authenticated"}
        token=jwt.encode(claims,private,algorithm="RS256",headers={"kid":"local-test"})
        return {"access_token":token,"refresh_token":"local-test-refresh:"+uid,"token_type":"bearer",
                "expires_in":3600,"expires_at":int(time.time())+3600,"user":user(uid,email)}

    @router.get("/.well-known/jwks.json",response_model=dict,status_code=200)
    async def keys():
        return jwks

    @router.post("/token",response_model=dict,status_code=200)
    async def sign_in(request:Request):
        body=await request.json()
        email=str(body.get("email","")).lower()
        if request.query_params.get("grant_type")=="refresh_token":
            uid=str(body.get("refresh_token","")).removeprefix("local-test-refresh:")
            if uid not in {f["customer"],f["owner"]}:
                return JSONResponse({"error":"invalid_grant"},status_code=400)
            email="owner@example.com" if uid==f["owner"] else "customer@example.com"
        elif email not in {"customer@example.com","owner@example.com"} or body.get("password")!="LocalTest123!":
            return JSONResponse({"error":"invalid_grant","error_description":"Use a local fixture account"},status_code=400)
        uid=f["owner"] if email=="owner@example.com" else f["customer"]
        return session(uid,email)

    @router.get("/user",response_model=dict,status_code=200)
    async def get_user(request:Request):
        try:
            uid=await deps._jwt_verifier.verify_subject(request.headers.get("authorization","").removeprefix("Bearer "))
        except Exception:
            return JSONResponse({"error":"unauthorized"},status_code=401)
        return user(uid,"owner@example.com" if uid==f["owner"] else "customer@example.com")

    # Synthetic phone identities only. No SMS provider or external network call.
    phones={"+919000000001":("customer","customer@example.com"),
            "+919000000002":("owner","owner@example.com")}

    @router.post("/otp",response_model=dict,status_code=200)
    async def phone_otp(request:Request):
        body=await request.json()
        if body.get("phone") not in phones:
            return JSONResponse({"error":"invalid_fixture"},status_code=400)
        return {"message_id":"synthetic-no-sms"}

    @router.post("/verify",response_model=dict,status_code=200)
    async def phone_verify(request:Request):
        body=await request.json()
        identity=phones.get(body.get("phone"))
        if identity is None or body.get("token")!="000000" or body.get("type")!="sms":
            return JSONResponse({"error":"invalid_fixture"},status_code=400)
        role,email=identity
        result=session(f[role],email)
        result["user"]["phone"]=body["phone"]
        result["user"]["phone_confirmed_at"]="2026-01-01T00:00:00Z"
        return result

    @router.post("/recover",response_model=dict,status_code=200)
    async def recover():
        return {}  # Test-double acknowledgement ONLY: no email is sent.

    @router.post("/logout",response_model=dict,status_code=200)
    async def logout():
        return {}

    app.include_router(router)
    # Production telemetry initialization never receives credentials in this process.
    from app.core.logging import configure_logging
    configure_logging(json_logs=True)
    return app


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--admin-url",default="postgresql://postgres@127.0.0.1:55439/postgres")
    args=parser.parse_args()
    if args.prepare:
        asyncio.run(prepare(args.admin_url))
    else:
        import uvicorn
        uvicorn.run(app_factory(),host="127.0.0.1",port=8050,access_log=False)
