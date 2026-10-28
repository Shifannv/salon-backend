"""Supabase Auth admin adapter contracts; no real network calls."""

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.supabase.auth_admin import SupabaseAuthAdminGateway


@pytest.mark.asyncio
async def test_unban_user_sends_the_supported_none_duration(monkeypatch):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "owner-001"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    gateway = SupabaseAuthAdminGateway(
        Settings(
            supabase_url="https://example.supabase.co",
            supabase_service_role_key="test-service-key",
        )
    )

    await gateway.unban_user("owner-001")

    assert len(seen) == 1
    assert seen[0].method == "PUT"
    assert seen[0].url.path == "/auth/v1/admin/users/owner-001"
    assert seen[0].read() == b'{"ban_duration":"none"}'
