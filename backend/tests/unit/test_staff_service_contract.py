"""Input bounds and safe unavailable-schema behavior for the visit contract."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import ProgrammingError

from app.core.exceptions import ServiceUnavailableError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository


async def test_missing_visit_migration_returns_service_unavailable_without_raw_sql():
    session = SimpleNamespace(execute=AsyncMock(), rollback=AsyncMock())
    original = type("MissingFunction", (Exception,), {"sqlstate":"42883"})("private SQL")
    session.execute.side_effect = ProgrammingError("select private_sql", {}, original)
    repository = PlatformRepository(session)
    with pytest.raises(ServiceUnavailableError) as caught:
        await repository.create_booking({"actor_id":"actor", "service_ids":["service"], "segments":[{"staff_id":"staff","service_ids":["service"]}]})
    assert "private" not in str(caught.value)
    session.rollback.assert_awaited_once()


async def test_absent_itinerary_keeps_legacy_retry_fingerprint():
    session = SimpleNamespace(execute=AsyncMock(), rollback=AsyncMock())
    repository = PlatformRepository(session)
    repository.begin_booking_operation = AsyncMock(return_value={"id":"legacy-booking"})
    result = await repository.create_booking({"actor_id":"actor", "service_ids":["service"], "segments":None})
    assert result["id"] == "legacy-booking"
    assert "segments" not in repository.begin_booking_operation.call_args.args[3]
