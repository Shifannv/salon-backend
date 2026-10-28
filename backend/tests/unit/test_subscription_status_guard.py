"""Admin suspend/cancel must only move a subscription out of allowed source states."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.use_cases.subscription import SalonSubscriptionUseCases
from app.core.exceptions import ConflictError, NotFoundError
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.subscription_repository import (
    SalonSubscriptionRepo,
)

_CANCELLED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class _Result:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def one_or_none(self):
        return self._row


class _FakeSession:
    """Emulates the guarded UPDATE and the follow-up SELECT for one subscription row."""

    def __init__(self, row):
        self.row = row
        self.commits = 0

    async def execute(self, statement, params=None):
        sql = str(statement).lower()
        if sql.lstrip().startswith("update"):
            allowed = params.get("allowed")
            if self.row is None or (allowed is not None and self.row["status"] not in allowed):
                return _Result(None)
            self.row = {
                **self.row,
                "status": params["status"],
                **{k: v for k, v in params.items() if k == "cancelled_at"},
            }
            return _Result(self.row)
        return _Result(self.row)

    async def commit(self):
        self.commits += 1


def _admin() -> Profile:
    return Profile(
        id=uuid4(), role=Role.super_admin, full_name="A", is_active=True,
        email=None, phone=None, phone_verified=False, avatar_url=None,
    )


def _uc(status, cancelled_at=None):
    row = None if status is None else {"id": "s1", "status": status, "cancelled_at": cancelled_at}
    session = _FakeSession(row)
    return SalonSubscriptionUseCases(SalonSubscriptionRepo(session), SimpleNamespace()), session


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["pending", "trialing", "active", "past_due", "suspended"])
async def test_cancel_allowed_from(source):
    uc, _ = _uc(source)
    result = await uc.cancel_subscription(_admin(), "s1")
    assert result["status"] == "cancelled"
    assert result["cancelled_at"] is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["pending", "trialing", "active", "past_due"])
async def test_suspend_allowed_from(source):
    uc, _ = _uc(source)
    assert (await uc.suspend_subscription(_admin(), "s1"))["status"] == "suspended"


@pytest.mark.asyncio
async def test_cancel_from_expired_conflicts():
    uc, session = _uc("expired")
    with pytest.raises(ConflictError):
        await uc.cancel_subscription(_admin(), "s1")
    assert session.row["status"] == "expired"
    assert session.commits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["cancelled", "expired"])
async def test_suspend_from_terminal_conflicts(source):
    uc, session = _uc(source)
    with pytest.raises(ConflictError):
        await uc.suspend_subscription(_admin(), "s1")
    assert session.row["status"] == source


@pytest.mark.asyncio
async def test_repeat_cancel_is_idempotent_and_keeps_cancelled_at():
    uc, session = _uc("cancelled", cancelled_at=_CANCELLED_AT)
    result = await uc.cancel_subscription(_admin(), "s1")
    assert result["status"] == "cancelled"
    assert result["cancelled_at"] == _CANCELLED_AT
    assert session.row["cancelled_at"] == _CANCELLED_AT


@pytest.mark.asyncio
async def test_repeat_suspend_is_idempotent():
    uc, _ = _uc("suspended")
    assert (await uc.suspend_subscription(_admin(), "s1"))["status"] == "suspended"


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["cancel_subscription", "suspend_subscription"])
async def test_missing_subscription_is_not_found(action):
    uc, _ = _uc(None)
    with pytest.raises(NotFoundError):
        await getattr(uc, action)(_admin(), "s1")
