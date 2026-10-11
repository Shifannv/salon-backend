"""list_bookings scoping: owner/staff see only their salon's bookings, never personal ones."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.db.repositories.platform_repository import PlatformRepository


async def _list_sql(role: str) -> str:
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    session.execute.return_value = result
    await PlatformRepository(session).list_bookings("actor-1", role)
    return str(session.execute.await_args.args[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["owner", "staff"])
async def test_salon_roles_are_not_matched_on_their_personal_customer_bookings(role):
    sql = await _list_sql(role)
    assert "b.customer_id = :actor_id" not in sql
    assert "s2.owner_id = :actor_id" in sql
    assert "st2.profile_id = :actor_id" in sql


@pytest.mark.asyncio
async def test_customer_role_still_sees_only_own_bookings():
    sql = await _list_sql("customer")
    assert "b.customer_id = :actor_id" in sql
    assert "s2.owner_id" not in sql
