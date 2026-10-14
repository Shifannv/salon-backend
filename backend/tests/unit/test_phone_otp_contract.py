"""Exercise the provider HTTP boundary, not a permissive gateway fake."""

import json

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.infrastructure.supabase.auth_gateway import SupabaseAuthGateway


@pytest.mark.parametrize("valid", [True, False])
async def test_phone_otp_uses_supabase_verify_and_preserves_rejection(monkeypatch, valid):
    requests = []

    def provider(request):
        requests.append(request)
        assert request.url.path == "/auth/v1/verify"
        assert not request.url.query
        assert json.loads(request.content) == {
            "phone": "+919000000001", "token": "123456", "type": "sms",
        }
        return httpx.Response(
            200 if valid else 400,
            json={"access_token": "synthetic-access", "refresh_token": "synthetic-refresh",
                  "expires_in": 3600} if valid else {"error": "invalid_otp"},
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(
        **kwargs, transport=httpx.MockTransport(provider)))
    gateway = SupabaseAuthGateway(Settings(
        supabase_url="http://127.0.0.1:8050", supabase_anon_key="local-test-public-key"))
    if valid:
        assert (await gateway.verify_phone_otp("+919000000001", "123456")).access_token == "synthetic-access"
    else:
        with pytest.raises(UnauthorizedError):
            await gateway.verify_phone_otp("+919000000001", "123456")
    assert len(requests) == 1
