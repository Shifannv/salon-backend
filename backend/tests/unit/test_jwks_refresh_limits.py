"""Unknown JWT keys cannot amplify outbound JWKS requests."""

import asyncio
import time

import pytest

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.security import SupabaseJWTVerifier


def verifier():
    return SupabaseJWTVerifier(Settings(_env_file=None))


async def test_concurrent_unknown_keys_share_one_cold_refresh():
    v = verifier()
    calls = []
    async def refresh():
        calls.append(1)
        await asyncio.sleep(0.01)
        v._jwks = {'keys': [{'kid': 'valid'}]}
        v._jwks_fetched_at = time.monotonic()
    v._refresh_jwks = refresh
    results = await asyncio.gather(*(v._get_key('unknown-'+str(i)) for i in range(30)), return_exceptions=True)
    assert all(isinstance(r, UnauthorizedError) for r in results)
    assert len(calls) == 1
    assert await v._get_key('valid') == {'kid': 'valid'}


async def test_rotation_refresh_is_allowed_after_bounded_cooldown(monkeypatch):
    v = verifier()
    clock = [1000.0]
    monkeypatch.setattr('app.core.security.time.monotonic', lambda: clock[0])
    calls = []
    async def refresh():
        calls.append(1)
        v._jwks = {'keys': [{'kid': 'old' if len(calls) == 1 else 'rotated'}]}
        v._jwks_fetched_at = clock[0]
    v._refresh_jwks = refresh
    assert await v._get_key('old') == {'kid': 'old'}
    with pytest.raises(UnauthorizedError):
        await v._get_key('rotated')
    assert len(calls) == 1
    clock[0] += 31
    assert await v._get_key('rotated') == {'kid': 'rotated'}
    assert len(calls) == 2


async def test_failed_fetch_attempts_are_also_bounded():
    v = verifier()
    calls = []
    async def refresh():
        calls.append(1)
        raise OSError('synthetic offline')
    v._refresh_jwks = refresh
    with pytest.raises(OSError):
        await v._get_key('unknown')
    with pytest.raises(UnauthorizedError):
        await v._get_key('another-unknown')
    assert len(calls) == 1
