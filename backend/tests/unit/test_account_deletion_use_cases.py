"""Account deletion verification and confirmation rules (in-memory fakes)."""

import logging
from datetime import UTC, datetime, timedelta
from itertools import count

import pytest

from app.application.ports.auth_admin_gateway import AuthUserContacts
from app.application.use_cases.account_deletion import (
    AccountDeletionUseCases,
    mask_contact,
    normalize_contact,
)
from app.core.config import Settings
from app.core.exceptions import (
    ContactMismatchError,
    DeletionBlockedError,
    ForbiddenError,
    InvalidVerificationCodeError,
    NotFoundError,
    ServiceUnavailableError,
    TooManyRequestsError,
)
from app.core.tokens import digests_match
from app.domain.entities.profile import Role
from tests.conftest import make_owner, make_profile, make_super_admin

CODE = "123456"


class FakeAuthGateway:
    def __init__(self, user_id: str = "user-001") -> None:
        self.user_id = user_id
        self.sent: list[tuple[str, str]] = []

    async def send_verification_code(self, channel: str, destination: str) -> None:
        self.sent.append((channel, destination))

    async def verify_code_user_id(self, channel: str, destination: str, code: str) -> str:
        if code != CODE:
            raise InvalidVerificationCodeError("The verification code is invalid or expired")
        return self.user_id


class FakeAuthAdmin:
    def __init__(self, contacts: AuthUserContacts | None) -> None:
        self.contacts = contacts

    async def get_user(self, user_id: str) -> AuthUserContacts | None:
        return self.contacts


class FakeRepo:
    """Mirrors the SQL adapter's state machine closely enough to test the use case."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.ids = count(1)
        self.blockers = {"open_bookings": 0, "pending_requests": 0, "active_subscriptions": 0}
        self.impact = 0
        self.requests: dict[str, dict] = {}
        self.confirmed: list[tuple[str, str]] = []

    def _view(self, row: dict) -> dict:
        age = (datetime.now(UTC) - row["last_sent_at"]).total_seconds()
        return {**row, "seconds_since_sent": age}

    async def count_blockers(self, user_id, role):
        return self.blockers

    async def count_closure_impact(self, user_id):
        return {"bookings_to_cancel": self.impact, "requests_to_resolve": 0}

    async def count_recent_challenges(self, user_id, window_seconds):
        return sum(1 for r in self.rows.values() if r["user_id"] == user_id)

    async def get_live_challenge(self, user_id):
        for row in self.rows.values():
            if row["user_id"] == user_id and row["status"] in {"sent", "verified"}:
                return self._view(row)
        return None

    async def expire_live_challenge(self, user_id):
        for row in self.rows.values():
            if row["user_id"] == user_id and row["status"] in {"sent", "verified"}:
                row["status"] = "expired"

    async def create_challenge(self, user_id, channel, contact_hash, ttl_seconds, max_attempts):
        cid = f"challenge-{next(self.ids)}"
        now = datetime.now(UTC)
        self.rows[cid] = {
            "id": cid, "user_id": user_id, "channel": channel, "contact_hash": contact_hash,
            "status": "sent", "attempts": 0, "max_attempts": max_attempts, "resend_count": 0,
            "last_sent_at": now, "expires_at": now + timedelta(seconds=ttl_seconds),
            "confirmation_hash": None,
        }
        return self._view(self.rows[cid])

    async def resend_challenge(self, challenge_id, channel, contact_hash, ttl_seconds):
        row = self.rows[challenge_id]
        row.update(channel=channel, contact_hash=contact_hash,
                   resend_count=row["resend_count"] + 1, last_sent_at=datetime.now(UTC))
        return self._view(row)

    async def get_challenge(self, challenge_id, user_id):
        row = self.rows.get(challenge_id)
        return self._view(row) if row and row["user_id"] == user_id else None

    async def begin_verify_attempt(self, challenge_id, user_id):
        row = self.rows.get(challenge_id)
        if not row or row["user_id"] != user_id or row["status"] != "sent":
            return None
        if row["attempts"] >= row["max_attempts"]:
            return None
        row["attempts"] += 1
        return self._view(row)

    async def expire_challenge(self, challenge_id):
        if self.rows[challenge_id]["status"] == "sent":
            self.rows[challenge_id]["status"] = "expired"

    async def mark_verified(self, challenge_id, user_id, confirmation_hash, ttl_seconds):
        row = self.rows.get(challenge_id)
        if not row or row["user_id"] != user_id or row["status"] != "sent":
            return None
        row.update(status="verified", confirmation_hash=confirmation_hash)
        return {"id": challenge_id,
                "confirmation_expires_at": datetime.now(UTC) + timedelta(seconds=ttl_seconds)}

    async def confirm_deletion(self, user_id, challenge_id, confirmation_hash):
        row = self.rows.get(challenge_id)
        # Idempotency: challenge already consumed for this user with a matching hash.
        if (row and row["user_id"] == user_id and row["status"] == "consumed"
                and digests_match(row["confirmation_hash"], confirmation_hash)):
            existing = next(
                (r for r in self.requests.values() if r["status"] != "completed"),
                None,
            )
            if existing is not None:
                return existing
        if (not row or row["user_id"] != user_id or row["status"] != "verified"
                or not digests_match(row["confirmation_hash"], confirmation_hash)):
            raise InvalidVerificationCodeError("The confirmation is invalid or expired")
        row["status"] = "consumed"
        self.confirmed.append((user_id, challenge_id))
        request = {"id": "11111111-1111-1111-1111-111111111111", "status": "pending",
                   "requested_at": datetime.now(UTC), "completed_at": None}
        self.requests[request["id"]] = request
        return request

    async def get_request(self, request_id):
        return self.requests.get(request_id)

    async def list_requests(self, limit, offset):
        return list(self.requests.values())


def contacts(**overrides) -> AuthUserContacts:
    values = {"user_id": "user-001", "email": "Test@Example.com", "email_verified": True,
              "phone": "+919876543210", "phone_verified": True}
    return AuthUserContacts(**{**values, **overrides})


def build(actor_contacts=None, user_id="user-001", **settings_kwargs):
    repo, gateway = FakeRepo(), FakeAuthGateway(user_id)
    settings = Settings(_env_file=None, environment="test", **settings_kwargs)
    admin = FakeAuthAdmin(actor_contacts if actor_contacts is not None else contacts())
    return AccountDeletionUseCases(repo, gateway, admin, settings), repo, gateway


async def verified_flow(uc, actor):
    started = await uc.start_challenge(actor, "email", None)
    verified = await uc.verify_challenge(actor, started["challenge_id"], CODE)
    return started["challenge_id"], verified["confirmation_token"]


def test_normalization_and_masking():
    assert normalize_contact("email", " A@B.Com ") == "a@b.com"
    assert normalize_contact("phone", "+91 98765-43210") == "+919876543210"
    assert mask_contact("email", "alice@example.com") == "a***@example.com"
    assert mask_contact("phone", "+919876543210").endswith("3210")
    assert "98765" not in mask_contact("phone", "+919876543210")


@pytest.mark.asyncio
@pytest.mark.parametrize("make_actor", [make_profile, make_owner])
async def test_code_goes_only_to_the_accounts_own_verified_contact(make_actor):
    uc, _, gateway = build()
    result = await uc.start_challenge(make_actor(), "email", "test@example.com")
    assert gateway.sent == [("email", "test@example.com")]
    assert result["masked_destination"] == "t***@example.com"


@pytest.mark.asyncio
async def test_client_cannot_redirect_the_code_to_another_identifier():
    uc, repo, gateway = build()
    with pytest.raises(ContactMismatchError):
        await uc.start_challenge(make_profile(), "email", "attacker@example.com")
    with pytest.raises(ContactMismatchError):
        await uc.start_challenge(make_profile(), "phone", "+15550001111")
    assert gateway.sent == []
    assert repo.rows == {}


@pytest.mark.asyncio
async def test_unverified_or_missing_contact_is_rejected():
    uc, _, gateway = build(contacts(email_verified=False))
    with pytest.raises(ContactMismatchError):
        await uc.start_challenge(make_profile(), "email", None)
    uc, _, gateway = build(contacts(phone=None, phone_verified=False))
    with pytest.raises(ContactMismatchError):
        await uc.start_challenge(make_profile(), "phone", None)
    assert gateway.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.staff, Role.super_admin])
async def test_other_roles_cannot_self_delete(role):
    uc, _, gateway = build()
    with pytest.raises(ForbiddenError):
        await uc.start_challenge(make_profile(role=role), "email", None)
    assert gateway.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize("blocker", ["open_bookings", "pending_requests"])
async def test_open_work_blocks_before_any_code_is_sent(blocker):
    # Customers only: the SQL adapter never reports open bookings/requests for an owner.
    uc, repo, gateway = build()
    repo.blockers[blocker] = 2
    with pytest.raises(DeletionBlockedError) as error:
        await uc.start_challenge(make_profile(), "email", None)
    assert error.value.status_code == 409 and error.value.code == "deletion_blocked"
    assert gateway.sent == []


@pytest.mark.asyncio
async def test_deletion_blocked_error_carries_structured_counts():
    uc, repo, _ = build()
    repo.blockers["open_bookings"] = 3
    repo.blockers["pending_requests"] = 1
    with pytest.raises(DeletionBlockedError) as exc_info:
        await uc.start_challenge(make_profile(), "email", None)
    details = exc_info.value.details
    assert details is not None
    assert details["open_bookings"] == 3
    assert details["pending_requests"] == 1


@pytest.mark.asyncio
async def test_confirm_idempotency_returns_existing_request_when_account_already_locked():
    """Concurrent second confirm (profile already inactive, challenge consumed) returns same request."""
    uc, repo, _ = build()
    actor = make_profile()
    challenge_id, token = await verified_flow(uc, actor)
    first = await uc.confirm(actor, challenge_id, token)

    # Simulate the state the SQL repo puts things in after a successful first confirm:
    # challenge is consumed, and repo has the request.  A concurrent second call
    # with the same inputs should get the same result back, not an error.
    row = repo.rows[challenge_id]
    assert row["status"] == "consumed"
    second = await uc.confirm(actor, challenge_id, token)
    assert second["request_id"] == first["request_id"]
    assert second["status_token"] == first["status_token"]
    assert len(repo.confirmed) == 1  # erasure queued only once


@pytest.mark.asyncio
async def test_active_subscription_blocks_only_with_a_real_provider():
    uc, repo, _ = build()
    repo.blockers["active_subscriptions"] = 1
    await uc.start_challenge(make_owner(), "email", None)
    uc, repo, gateway = build(subscription_provider="stripe")
    repo.blockers["active_subscriptions"] = 1
    with pytest.raises(DeletionBlockedError):
        await uc.start_challenge(make_owner(), "email", None)
    assert gateway.sent == []


@pytest.mark.asyncio
async def test_resend_cooldown_and_cap_are_enforced():
    uc, repo, gateway = build(account_deletion_max_resends=1)
    actor = make_profile()
    await uc.start_challenge(actor, "email", None)
    with pytest.raises(TooManyRequestsError):
        await uc.start_challenge(actor, "email", None)
    row = next(iter(repo.rows.values()))
    row["last_sent_at"] -= timedelta(seconds=120)
    await uc.start_challenge(actor, "email", None)
    assert len(gateway.sent) == 2 and row["resend_count"] == 1
    row["last_sent_at"] -= timedelta(seconds=120)
    with pytest.raises(TooManyRequestsError):
        await uc.start_challenge(actor, "email", None)
    assert len(gateway.sent) == 2


@pytest.mark.asyncio
async def test_hourly_challenge_cap():
    uc, repo, _ = build(account_deletion_max_challenges_per_hour=1)
    actor = make_profile()
    await uc.start_challenge(actor, "email", None)
    next(iter(repo.rows.values()))["status"] = "expired"
    with pytest.raises(TooManyRequestsError):
        await uc.start_challenge(actor, "email", None)


@pytest.mark.asyncio
async def test_happy_path_requires_verification_then_explicit_confirmation():
    uc, repo, _ = build()
    actor = make_profile()
    challenge_id, token = await verified_flow(uc, actor)
    assert repo.confirmed == []  # verification alone deletes nothing
    accepted = await uc.confirm(actor, challenge_id, token)
    assert repo.confirmed == [("user-001", challenge_id)]
    assert accepted["status"] == "pending" and accepted["status_token"]
    status = await uc.get_status(accepted["request_id"], accepted["status_token"])
    assert status["status"] == "pending"


@pytest.mark.asyncio
async def test_confirm_rejects_wrong_token_and_unverified_challenge():
    uc, repo, _ = build()
    actor = make_profile()
    challenge_id, token = await verified_flow(uc, actor)
    with pytest.raises(InvalidVerificationCodeError):
        await uc.confirm(actor, challenge_id, "x" * 43)
    started = await uc.start_challenge(make_profile(id="user-002"), "email", None)
    with pytest.raises(InvalidVerificationCodeError):  # sent, never verified
        await uc.confirm(make_profile(id="user-002"), started["challenge_id"], token)
    await uc.confirm(actor, challenge_id, token)
    assert len(repo.confirmed) == 1


@pytest.mark.asyncio
async def test_confirm_replay_with_consumed_token_returns_same_request_not_error():
    """Replaying the same challenge + token after success returns the existing request."""
    uc, repo, _ = build()
    actor = make_profile()
    challenge_id, token = await verified_flow(uc, actor)
    first = await uc.confirm(actor, challenge_id, token)
    second = await uc.confirm(actor, challenge_id, token)  # idempotent, must not raise
    assert second["request_id"] == first["request_id"]
    assert len(repo.confirmed) == 1  # erasure queued exactly once


@pytest.mark.asyncio
async def test_challenge_and_token_cannot_authorize_another_account():
    uc, repo, _ = build()
    victim, attacker = make_profile(id="user-001"), make_profile(id="user-002")
    challenge_id, token = await verified_flow(uc, victim)
    with pytest.raises(NotFoundError):
        await uc.verify_challenge(attacker, challenge_id, CODE)
    with pytest.raises(InvalidVerificationCodeError):
        await uc.confirm(attacker, challenge_id, token)
    assert repo.confirmed == []


@pytest.mark.asyncio
async def test_wrong_codes_exhaust_attempts_then_even_the_right_code_fails():
    uc, repo, _ = build(account_deletion_max_attempts=2)
    actor = make_profile()
    started = await uc.start_challenge(actor, "email", None)
    for _ in range(2):
        with pytest.raises(InvalidVerificationCodeError):
            await uc.verify_challenge(actor, started["challenge_id"], "000000")
    assert repo.rows[started["challenge_id"]]["status"] == "expired"
    with pytest.raises(InvalidVerificationCodeError):
        await uc.verify_challenge(actor, started["challenge_id"], CODE)


@pytest.mark.asyncio
async def test_code_that_authenticates_a_different_user_is_rejected_and_burns_the_challenge():
    uc, repo, _ = build(user_id="someone-else")
    actor = make_profile()
    started = await uc.start_challenge(actor, "email", None)
    with pytest.raises(InvalidVerificationCodeError):
        await uc.verify_challenge(actor, started["challenge_id"], CODE)
    assert repo.rows[started["challenge_id"]]["status"] == "expired"


@pytest.mark.asyncio
async def test_verified_challenge_cannot_be_verified_twice():
    uc, _, _ = build()
    actor = make_profile()
    started = await uc.start_challenge(actor, "email", None)
    await uc.verify_challenge(actor, started["challenge_id"], CODE)
    with pytest.raises(InvalidVerificationCodeError):
        await uc.verify_challenge(actor, started["challenge_id"], CODE)


@pytest.mark.asyncio
async def test_contact_change_after_challenge_invalidates_it():
    uc, _, _ = build()
    actor = make_profile()
    started = await uc.start_challenge(actor, "email", None)
    uc.auth_admin.contacts = contacts(email="new@example.com")
    with pytest.raises(InvalidVerificationCodeError):
        await uc.verify_challenge(actor, started["challenge_id"], CODE)


@pytest.mark.asyncio
async def test_status_requires_the_matching_token():
    uc, _, _ = build()
    actor = make_profile()
    challenge_id, token = await verified_flow(uc, actor)
    accepted = await uc.confirm(actor, challenge_id, token)
    with pytest.raises(NotFoundError):
        await uc.get_status(accepted["request_id"], "wrong-token-wrong-token-wrong")
    with pytest.raises(NotFoundError):
        await uc.get_status("22222222-2222-2222-2222-222222222222", accepted["status_token"])


@pytest.mark.asyncio
async def test_missing_secret_outside_local_returns_503_not_an_insecure_default():
    settings = Settings(
        _env_file=None, environment="production", supabase_url="https://x.supabase.co",
        supabase_anon_key="anon", supabase_jwks_url="https://x.supabase.co/jwks",
        supabase_service_role_key="service",
    )
    uc = AccountDeletionUseCases(FakeRepo(), FakeAuthGateway(), FakeAuthAdmin(contacts()), settings)
    with pytest.raises(ServiceUnavailableError):
        await uc.start_challenge(make_profile(), "email", None)
    with pytest.raises(ServiceUnavailableError):
        await uc.get_status("11111111-1111-1111-1111-111111111111", "t" * 30)


@pytest.mark.asyncio
async def test_admin_ledger_requires_super_admin():
    uc, _, _ = build()
    with pytest.raises(ForbiddenError):
        await uc.list_requests(make_owner(), 10, 0)
    assert await uc.list_requests(make_super_admin(), 10, 0) == []


@pytest.mark.asyncio
async def test_no_otp_token_or_contact_is_logged(caplog):
    caplog.set_level(logging.DEBUG)
    uc, _, _ = build()
    actor = make_profile()
    challenge_id, token = await verified_flow(uc, actor)
    accepted = await uc.confirm(actor, challenge_id, token)
    text = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (CODE, token, accepted["status_token"], "test@example.com", "+919876543210"):
        assert secret not in text


@pytest.mark.asyncio
async def test_owner_is_told_how_many_bookings_will_be_cancelled_not_blocked():
    uc, repo, gateway = build()
    repo.impact = 4
    result = await uc.start_challenge(make_owner(), "email", None)
    assert result["bookings_to_cancel"] == 4 and gateway.sent
    customer = await uc.start_challenge(make_profile(), "email", None)
    assert customer["bookings_to_cancel"] == 0


def test_deletion_stage_progresses_through_the_cancel_refund_erase_phases():
    from app.application.use_cases.account_deletion import deletion_stage

    assert deletion_stage("pending", {}) == "queued"
    assert deletion_stage("processing", {"bookings_cancelled": True}) == "refunding"
    assert deletion_stage("pending", {"bookings_cancelled": True, "refunds_issued": True}) == "waiting_for_refunds"
    assert deletion_stage("processing", {"refunds_settled": True}) == "erasing"
    assert deletion_stage("processing", {"db_erased": True}) == "erasing"
    assert deletion_stage("completed", {}) == "completed"
