"""Provision or re-key the super-admin account.

Run from ``backend/``:

    python -m scripts.provision_super_admin --email admin@example.com --yes

The password is read from the ``SUPER_ADMIN_PASSWORD`` environment variable or
from an interactive getpass prompt.  It is never passed on the command line,
never logged, and never written to disk.

The script is idempotent: calling it a second time updates the password and
ensures the profile row has ``role='super_admin'`` and ``is_active=true``.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import os
import sys
from dataclasses import dataclass

import asyncpg
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass
class _AuthUser:
    user_id: str
    email: str


@dataclass
class _ProfileState:
    role: str
    is_active: bool
    owns_salon: bool


def _admin_base() -> tuple[str, dict[str, str]]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SystemExit(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment."
        )
    base_url = str(settings.supabase_url).rstrip("/")
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    return base_url, headers


async def _find_user_by_email(
    base_url: str, headers: dict[str, str], email: str
) -> _AuthUser | None:
    """Return the Supabase Auth user for *email*, or None."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{base_url}/auth/v1/admin/users",
            params={"page": 1, "per_page": 1000},
            headers=headers,
        )
    if response.is_error:
        raise RuntimeError(f"Could not list Supabase users: HTTP {response.status_code}")
    data = response.json()
    for user in data.get("users", []):
        if (user.get("email") or "").lower() == email.lower():
            return _AuthUser(user_id=str(user["id"]), email=user["email"])
    return None


async def _create_auth_user(
    base_url: str, headers: dict[str, str], email: str, password: str
) -> _AuthUser:
    """Create a new Supabase Auth user with email_confirm=true."""
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "app_metadata": {"role": "super_admin"},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{base_url}/auth/v1/admin/users",
            json=payload,
            headers=headers,
        )
    if response.is_error:
        raise RuntimeError(f"Could not create Supabase Auth user: HTTP {response.status_code}")
    data = response.json()
    return _AuthUser(user_id=str(data["id"]), email=str(data["email"]))


async def _update_auth_password(
    base_url: str, headers: dict[str, str], user_id: str, password: str
) -> None:
    """Update an existing Supabase Auth user's password."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.put(
            f"{base_url}/auth/v1/admin/users/{user_id}",
            json={"password": password},
            headers=headers,
        )
    if response.is_error:
        raise RuntimeError(
            f"Could not update password for user {user_id}: HTTP {response.status_code}"
        )


async def _upsert_profile(database_url: str, user_id: str, email: str) -> None:
    """Ensure the profiles row has role='super_admin' and is_active=true."""
    conn_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    connection = await asyncpg.connect(conn_url, timeout=15, statement_cache_size=0)
    try:
        await connection.execute(
            """
            INSERT INTO public.profiles (id, email, role, is_active, created_at, updated_at)
            VALUES ($1, $2, 'super_admin', true, now(), now())
            ON CONFLICT (id) DO UPDATE
                SET role      = 'super_admin',
                    is_active = true,
                    updated_at = now()
            """,
            user_id,
            email,
        )
    finally:
        await connection.close()


async def _get_profile_state(database_url: str, user_id: str) -> _ProfileState | None:
    """Return the business role before changing any Auth credential."""
    conn_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    connection = await asyncpg.connect(conn_url, timeout=15, statement_cache_size=0)
    try:
        row = await connection.fetchrow(
            """
            SELECT p.role::text AS role,
                   p.is_active,
                   EXISTS (SELECT 1 FROM public.salons s WHERE s.owner_id = p.id) AS owns_salon
            FROM public.profiles p
            WHERE p.id = $1::uuid
            """,
            user_id,
        )
    finally:
        await connection.close()
    if row is None:
        return None
    return _ProfileState(
        role=str(row["role"]),
        is_active=bool(row["is_active"]),
        owns_salon=bool(row["owns_salon"]),
    )


def _assert_safe_existing_profile(state: _ProfileState | None) -> None:
    """Never silently turn a customer, owner, or staff identity into a platform admin."""
    if state is None or state.role == "super_admin":
        return
    ownership = " and owns a salon" if state.owns_salon else ""
    raise RuntimeError(
        f"Refusing to convert an existing {state.role} profile{ownership} into a "
        "super-admin. Provision a dedicated admin email instead."
    )


# ---------------------------------------------------------------------------
# Public entry point (also used by tests via dependency injection)
# ---------------------------------------------------------------------------


async def provision(
    email: str,
    password: str,
    *,
    auth_gateway: _FakeGateway | None = None,
) -> str:
    """Create or update the super-admin account. Returns the Supabase user id.

    ``auth_gateway`` is an optional test seam; in production the real Supabase
    Admin API is called directly.
    """
    email = email.strip().lower()
    if len(password) < 12:
        raise ValueError("Super-admin passwords must contain at least 12 characters.")

    if auth_gateway is not None:
        # Test path: delegate to the injected fake.
        user = await auth_gateway.ensure_super_admin(email, password)
        await auth_gateway.upsert_profile(user.user_id, user.email)
        return user.user_id

    # Production path.
    base_url, headers = _admin_base()

    existing = await _find_user_by_email(base_url, headers, email)
    if existing is not None:
        profile_state = await _get_profile_state(settings.database_url, existing.user_id)
        _assert_safe_existing_profile(profile_state)
        logger.info("Existing user found (%s), updating password…", existing.user_id)
        await _update_auth_password(base_url, headers, existing.user_id, password)
        user = existing
    else:
        logger.info("Creating new Supabase Auth user for %s…", email)
        user = await _create_auth_user(base_url, headers, email, password)

    logger.info("Upserting profile for %s (role=super_admin, is_active=true)…", user.user_id)
    await _upsert_profile(settings.database_url, user.user_id, user.email)

    logger.info("Done — super-admin %s is ready.", user.user_id)
    return user.user_id


# ---------------------------------------------------------------------------
# Fake gateway type hint (import guard so domain code stays clean)
# ---------------------------------------------------------------------------


class _FakeGateway:
    """Protocol satisfied by the fake in tests — not imported at module level."""

    async def ensure_super_admin(self, email: str, password: str) -> _AuthUser: ...
    async def upsert_profile(self, user_id: str, email: str) -> None: ...


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--email", required=True, help="Super-admin email address")
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Confirm you intend to modify the target environment. "
            "Required to prevent accidental runs."
        ),
    )
    args = parser.parse_args()

    if not args.yes:
        print(
            f"ERROR: This script modifies the {settings.environment!r} environment. "
            "Pass --yes to confirm.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # Read password from env (CI/scripts) or interactive prompt — never from argv.
    password: str = os.environ.get("SUPER_ADMIN_PASSWORD", "")
    if not password:
        try:
            password = getpass.getpass("Super-admin password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.", file=sys.stderr)
            raise SystemExit(1)

    if not password:
        print("ERROR: Password must not be empty.", file=sys.stderr)
        raise SystemExit(1)

    asyncio.run(provision(args.email, password))


if __name__ == "__main__":
    main()
