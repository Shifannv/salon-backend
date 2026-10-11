"""Unit tests for scripts.provision_super_admin."""

from __future__ import annotations

import pytest

from scripts.provision_super_admin import (
    _assert_safe_existing_profile,
    _AuthUser,
    _ProfileState,
    provision,
)

# ---------------------------------------------------------------------------
# Fake gateway
# ---------------------------------------------------------------------------


class FakeAuthGateway:
    """In-memory stand-in for the Supabase Admin API + asyncpg calls."""

    def __init__(self, existing_users: dict[str, str] | None = None) -> None:
        # email -> user_id for users that already exist
        self._users: dict[str, str] = dict(existing_users or {})
        self._created: list[tuple[str, str]] = []  # (email, password)
        self._updated: list[tuple[str, str]] = []  # (user_id, password)
        self._upserted: list[tuple[str, str]] = []  # (user_id, email)

    async def ensure_super_admin(self, email: str, password: str) -> _AuthUser:
        if email in self._users:
            user_id = self._users[email]
            self._updated.append((user_id, password))
        else:
            user_id = f"new-{len(self._users)}"
            self._users[email] = user_id
            self._created.append((email, password))
        return _AuthUser(user_id=user_id, email=email)

    async def upsert_profile(self, user_id: str, email: str) -> None:
        self._upserted.append((user_id, email))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provision_creates_new_user():
    gw = FakeAuthGateway()
    user_id = await provision("admin@example.com", "s3cr3t-long!", auth_gateway=gw)

    assert user_id == "new-0"
    assert len(gw._created) == 1
    assert gw._created[0] == ("admin@example.com", "s3cr3t-long!")
    assert len(gw._updated) == 0
    assert gw._upserted == [("new-0", "admin@example.com")]


@pytest.mark.asyncio
async def test_provision_updates_existing_user_password():
    gw = FakeAuthGateway(existing_users={"admin@example.com": "existing-uuid"})
    user_id = await provision("admin@example.com", "newpassword!", auth_gateway=gw)

    assert user_id == "existing-uuid"
    assert len(gw._created) == 0
    assert gw._updated == [("existing-uuid", "newpassword!")]
    assert gw._upserted == [("existing-uuid", "admin@example.com")]


@pytest.mark.asyncio
async def test_provision_normalises_email():
    """Email should be lowercased before lookup and storage."""
    gw = FakeAuthGateway(existing_users={"admin@example.com": "uuid-001"})
    user_id = await provision("ADMIN@EXAMPLE.COM", "long-password!", auth_gateway=gw)

    assert user_id == "uuid-001"
    # upserted with the normalised email
    assert gw._upserted[0][1] == "admin@example.com"


@pytest.mark.asyncio
async def test_provision_is_idempotent():
    """Calling provision twice should only create the user once."""
    gw = FakeAuthGateway()

    first_id = await provision("admin@example.com", "password-one!", auth_gateway=gw)
    second_id = await provision("admin@example.com", "password-two!", auth_gateway=gw)

    assert first_id == second_id
    assert len(gw._created) == 1
    assert len(gw._updated) == 1  # password refresh on second call
    assert len(gw._upserted) == 2  # profile upserted both times (idempotent)


def test_refuses_to_convert_an_existing_owner() -> None:
    with pytest.raises(RuntimeError, match="dedicated admin email"):
        _assert_safe_existing_profile(_ProfileState(role="owner", is_active=True, owns_salon=True))


def test_allows_an_existing_super_admin() -> None:
    _assert_safe_existing_profile(
        _ProfileState(role="super_admin", is_active=False, owns_salon=False)
    )


@pytest.mark.asyncio
async def test_rejects_short_password() -> None:
    with pytest.raises(ValueError, match="at least 12"):
        await provision("admin@example.com", "short", auth_gateway=FakeAuthGateway())
