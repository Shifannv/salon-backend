"""A customer cannot delete their account while any booking is still in progress.

``checked_in`` (the customer is in the chair right now) must block exactly like an upcoming
``pending``/``confirmed`` booking. The real-PostgreSQL behaviour is covered by
``tests/integration/test_account_deletion_sql.py``; this test pins the SQL predicate so the
gap cannot silently return when that opt-in suite is not run.
"""

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)


def _statuses(sql: str) -> set[str]:
    return set(re.findall(r"'(\w+)'", sql))


@pytest.mark.asyncio
async def test_customer_open_booking_blocker_includes_checked_in():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    session.execute.return_value = result

    await SQLAccountDeletionRepository(session).count_blockers("00000000-0000-0000-0000-000000000001", "customer")

    bookings_sql = str(session.execute.await_args_list[0].args[0])
    assert _statuses(bookings_sql) == {"pending", "confirmed", "checked_in"}
    # pending/confirmed block only while upcoming; checked_in blocks even if running over
    assert "b.status = 'checked_in'" in bookings_sql
    assert "b.end_datetime > now()" in bookings_sql
