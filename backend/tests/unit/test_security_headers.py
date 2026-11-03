"""Baseline security headers on API responses."""

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.security_headers import SecurityHeadersMiddleware


def client(environment="production"):
    async def plain(request):
        return JSONResponse({"ok": True})

    async def cached(request):
        return JSONResponse({"ok": True}, headers={"Cache-Control": "public, max-age=60", "Referrer-Policy": "origin"})

    app = Starlette(routes=[Route("/plain", plain), Route("/cached", cached)])
    app.add_middleware(SecurityHeadersMiddleware, environment=environment)
    return TestClient(app)


def test_every_response_gets_the_baseline_headers():
    r = client().get("/plain")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["strict-transport-security"] == "max-age=31536000"
    assert "cache-control" not in r.headers


def test_authenticated_responses_are_not_cacheable():
    assert client().get("/plain", headers={"Authorization": "Bearer x"}).headers["cache-control"] == "no-store"


def test_headers_a_route_already_set_are_kept():
    r = client().get("/cached", headers={"Authorization": "Bearer x"})
    assert r.headers["cache-control"] == "public, max-age=60"
    assert r.headers["referrer-policy"] == "origin"


def test_local_runs_do_not_send_hsts():
    assert "strict-transport-security" not in client("local").get("/plain").headers
