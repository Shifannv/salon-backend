"""Erasure worker: ordering, idempotent resume, provider failures, media safety."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.ports.auth_admin_gateway import AuthUserContacts
from app.application.use_cases.account_erasure import (
    AccountErasureService,
    managed_media_path,
)

BASE = "https://media.example.com"
BUCKET = "salon-images"
USER = "11111111-1111-1111-1111-111111111111"
SALON = "22222222-2222-2222-2222-222222222222"
STAFF_USER = "33333333-3333-3333-3333-333333333333"


class FakeStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.fail_for: set[str] = set()

    def get_public_url(self, bucket: str, path: str) -> str:
        return f"{BASE}/{path}"

    async def erasure_lock_paths(self, path: str) -> list[str]:
        return [path]

    async def erasure_paths(self, path: str) -> list[str]:
        return [path]

    async def delete_object(self, bucket: str, path: str) -> None:
        if path in self.fail_for:
            raise RuntimeError("r2 unavailable")
        self.deleted.append(path)


class FakeLedger:
    """Ledger/outbox semantics of the SQL adapter, kept in memory."""

    def __init__(self, request: dict) -> None:
        self.request = request
        self.status = "pending"
        self.error: str | None = None
        self.delay: int | None = None
        self.erased: list[tuple[str, str]] = []
        self.profile_present = True
        self.events: list[str] = []

    async def claim_due_request(self, stale_seconds):
        if self.status in {"completed"}:
            return None
        self.status = "processing"
        self.request["attempts"] += 1
        return {**self.request, "step_state": dict(self.request["step_state"])}

    async def record_step(self, request_id, step):
        self.request["step_state"][step] = True
        self.events.append(f"step:{step}")

    async def fail_request(self, request_id, error_code, delay_seconds):
        self.status, self.error, self.delay = "failed", error_code, delay_seconds

    async def complete_request(self, request_id):
        self.status = "completed"

    async def erase_database(self, user_id, role, staff_profile_ids=None):
        self.erased.append((user_id, role))
        self.profile_present = False
        self.events.append("db")

    async def profile_exists(self, user_id):
        return self.profile_present

    async def requeue_request(self, request_id, reason_code, delay_seconds):
        self.status, self.error, self.delay = "pending", reason_code, delay_seconds

    # Closure phase: no bookings, no payments (the PAYMENT_PROVIDER=none shape).
    async def cancel_open_bookings(self, user_id):
        self.events.append("cancel")
        return {"cancelled": 0, "notified": 0, "resolved": 0}

    async def list_closure_refund_candidates(self, user_id):
        return []

    async def list_unsettled_closure_refunds(self, user_id):
        return []


class FakeAdmin:
    def __init__(self) -> None:
        self.users = {USER, STAFF_USER}
        self.banned: list[str] = []
        self.delete_fail = False

    async def get_user(self, user_id):
        if user_id not in self.users:
            return None
        return AuthUserContacts(user_id, "a@b.c", True, None, False)

    async def ban_user(self, user_id):
        self.banned.append(user_id)

    async def delete_user(self, user_id):
        if self.delete_fail:
            raise RuntimeError("supabase down")
        self.users.discard(user_id)


def make_request(role="owner", media=None, staff_ids=None):
    return {
        "id": "req-1", "user_id": USER, "role": role,
        "salon_id": SALON if role == "owner" else None, "attempts": 0,
        "step_state": {"staff_profile_ids": staff_ids or []},
        "media_keys": media if media is not None else [],
    }


def make_service(request, *, referenced=()):
    ledger, admin, storage = FakeLedger(request), FakeAdmin(), FakeStorage()
    cache = MagicMock()
    cache.delete_prefix = AsyncMock()
    refs = MagicMock()
    refs.lock_media_url = AsyncMock()
    refs.media_url_is_referenced = AsyncMock(side_effect=lambda url: url in referenced)
    release = AsyncMock()
    cache.available = True
    service = AccountErasureService(ledger, admin, storage, cache, refs, release, BUCKET, 600)
    return service, ledger, admin, storage, cache, refs, release


@pytest.mark.asyncio
async def test_owner_erasure_runs_every_step_and_completes():
    media = [f"{BASE}/avatars/{USER}/a.jpg", f"{BASE}/salon-images/{SALON}/1.jpg"]
    service, ledger, admin, storage, cache, _, release = make_service(
        make_request(media=media, staff_ids=[STAFF_USER])
    )
    assert await service.process_next() is True
    assert ledger.status == "completed"
    assert admin.banned == [USER, STAFF_USER]
    assert ledger.erased == [(USER, "owner")]
    assert storage.deleted == [f"avatars/{USER}/a.jpg", f"salon-images/{SALON}/1.jpg"]
    assert release.await_count == 2
    assert USER not in admin.users
    prefixes = [call.args[0] for call in cache.delete_prefix.await_args_list]
    assert f"salon:{SALON}:" in prefixes and f"idempotency:walkin:v2:{USER}:" in prefixes
    assert STAFF_USER not in admin.users  # staff login removed once its profile is gone
    assert ledger.events == [
        "cancel", "step:bookings_cancelled", "step:refunds_issued", "step:refunds_settled",
        "step:auth_banned", "db", "step:db_erased", "step:media_deleted",
        "step:cache_cleared", "step:auth_deleted", "step:staff_auth_deleted",
    ]


@pytest.mark.asyncio
async def test_customer_erasure_skips_salon_cache_keys():
    service, ledger, _, _, cache, _, _ = make_service(make_request(role="customer"))
    await service.process_next()
    assert ledger.status == "completed"
    assert [c.args[0] for c in cache.delete_prefix.await_args_list] == [
        f"idempotency:walkin:v2:{USER}:", f"idempotency:booking:{USER}:",
    ]
    assert "cancel" not in ledger.events  # customers have no salon to close


@pytest.mark.asyncio
async def test_auth_delete_failure_is_retryable_and_resumes_without_repeating_steps(caplog):
    caplog.set_level(logging.DEBUG)
    service, ledger, admin, storage, _, _, _ = make_service(
        make_request(media=[f"{BASE}/avatars/{USER}/a.jpg"])
    )
    admin.delete_fail = True
    await service.process_next()
    assert ledger.status == "failed" and ledger.error == "RuntimeError" and ledger.delay >= 30
    assert ledger.request["step_state"]["db_erased"] is True
    assert USER in admin.users  # never reported as completed

    admin.delete_fail = False
    await service.process_next()
    assert ledger.status == "completed"
    assert len(ledger.erased) == 1  # DB erasure not repeated on resume
    assert admin.banned == [USER]
    assert storage.deleted == [f"avatars/{USER}/a.jpg"]
    assert "supabase down" not in "\n".join(r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_r2_failure_blocks_completion_until_retry_succeeds():
    path = f"avatars/{USER}/a.jpg"
    service, ledger, admin, storage, _, _, _ = make_service(
        make_request(media=[f"{BASE}/{path}"])
    )
    storage.fail_for.add(path)
    await service.process_next()
    assert ledger.status == "failed"
    assert USER in admin.users and "auth_deleted" not in ledger.request["step_state"]
    storage.fail_for.clear()
    await service.process_next()
    assert ledger.status == "completed" and storage.deleted == [path]


@pytest.mark.asyncio
async def test_shared_media_still_referenced_is_not_deleted():
    shared = f"{BASE}/salon-images/{SALON}/shared.jpg"
    service, ledger, _, storage, _, refs, release = make_service(
        make_request(media=[shared]), referenced={shared}
    )
    await service.process_next()
    assert ledger.status == "completed" and storage.deleted == []
    refs.lock_media_url.assert_awaited_once_with(shared)
    release.assert_awaited_once()


@pytest.mark.asyncio
async def test_lock_is_released_even_when_storage_fails():
    path = f"avatars/{USER}/a.jpg"
    service, _, _, storage, _, _, release = make_service(make_request(media=[f"{BASE}/{path}"]))
    storage.fail_for.add(path)
    await service.process_next()
    release.assert_awaited_once()


@pytest.mark.asyncio
async def test_verification_failure_keeps_request_open():
    service, ledger, *_ = make_service(make_request(role="customer"))
    ledger.erase_database = AsyncMock()  # profile row is never removed
    await service.process_next()
    assert ledger.status == "failed" and ledger.error == "ErasureVerificationError"


@pytest.mark.asyncio
async def test_already_missing_auth_user_is_not_banned_and_delete_is_idempotent():
    service, ledger, admin, _, _, _, _ = make_service(make_request(role="customer"))
    admin.users.discard(USER)
    await service.process_next()
    assert ledger.status == "completed" and admin.banned == []


@pytest.mark.asyncio
async def test_nothing_due_returns_false():
    service, ledger, *_ = make_service(make_request())
    ledger.status = "completed"
    assert await service.process_next() is False


@pytest.mark.asyncio
async def test_missing_storage_configuration_fails_instead_of_skipping_media():
    service, ledger, *_ = make_service(make_request(media=[f"{BASE}/avatars/{USER}/a.jpg"]))
    service.bucket = None
    service.storage_required = True
    await service.process_next()
    assert ledger.status == "failed" and ledger.error == "ErasureVerificationError"


@pytest.mark.asyncio
async def test_unconfigured_storage_in_local_dev_does_not_loop_forever_on_foreign_avatars():
    service, ledger, *_ = make_service(make_request(media=["https://lh3.googleusercontent.com/a"]))
    service.bucket = None  # storage_required stays False: nothing managed can exist
    await service.process_next()
    assert ledger.status == "completed"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"{BASE}/avatars/u/p.jpg", "avatars/u/p.jpg"),
        (f"{BASE}/staff-photos/s/p.png", "staff-photos/s/p.png"),
        (f"{BASE}/salon-images/s/p.webp", "salon-images/s/p.webp"),
        (f"{BASE}/other/u/p.jpg", None),
        (f"{BASE}/avatars/../secrets/key", None),
        (f"{BASE}/avatars/u//p.jpg", None),
        (f"{BASE}/avatars/u/p.jpg?x=1", None),
        (f"{BASE}/avatars/%2e%2e/x", None),
        (f"{BASE}/avatars/", None),
        ("https://evil.example.com/avatars/u/p.jpg", None),
        ("avatar:curly", None),
    ],
)
def test_only_platform_owned_object_keys_are_ever_deleted(url, expected):
    assert managed_media_path(FakeStorage(), BUCKET, url) == expected
