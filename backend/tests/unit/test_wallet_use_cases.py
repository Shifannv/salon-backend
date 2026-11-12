"""Owner wallet and admin payout use cases, against an in-memory repository."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.application.use_cases.wallet import WalletAdminUseCases, WalletUseCases
from app.core.exceptions import (
    ForbiddenError,
    IdempotencyKeyRequiredError,
    IdempotencyKeyReuseError,
    InsufficientBalanceError,
    NotFoundError,
    PayoutAccountMissingError,
    PayoutAlreadyProcessedError,
    PayoutBelowMinimumError,
    PayoutDayInvalidError,
    PayoutNotCancellableError,
    PayoutTransferInProgressError,
    SalonApprovalRequiredError,
    ValidationError,
)
from app.domain.entities.profile import Role
from app.domain.services.wallet import MIN_PAYOUT_PAISE
from tests.conftest import make_profile, make_super_admin

NOW = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)  # 12:00 on 1 Nov in India
TODAY = date(2026, 11, 1)
SALON = {
    "id": "salon-1", "timezone": "Asia/Kolkata", "is_active": True,
    "profile_completed": True, "approval_status": "approved",
}
KEY = "key-0000001"


class FakeWallet:
    """The slice of WalletRepository the use cases touch, with the same one-move status rule."""

    def __init__(self, *, collected: int = 500_000, commission: int = 50_000, account: bool = True) -> None:
        self.salon: dict[str, Any] | None = dict(SALON)
        self.collected, self.commission, self.account = collected, commission, account
        self.requests: dict[str, dict[str, Any]] = {}
        self.commits = 0
        self.locks = 0
        self.minimum: int | None = None  # None: the admin has not set one
        self.account_changed = False
        self.live: dict[str, Any] | None = None  # a pending or successful Cashfree transfer

    async def commit(self) -> None:
        self.commits += 1

    async def owner_salon(self, actor_id: str):
        return self.salon

    async def lock_salon(self, salon_id: str) -> None:
        self.locks += 1

    async def payout_account_ready(self, salon_id: str) -> bool:
        return self.account

    async def totals(self, salon_id: str) -> dict[str, int]:
        held = lambda status: sum(r["amount_paise"] for r in self.requests.values() if r["status"] == status)
        return {"collected": self.collected, "commission": self.commission, "refunded": 0, "reversed": 0,
                "requested": held("requested"), "paid": held("paid")}

    async def entries(self, salon_id: str, cursor, limit):
        return [], None

    async def stored_request(self, salon_id: str, key: str, request_hash: str):
        for row in self.requests.values():
            if row["idempotency_key"] == key:
                if row["request_hash"] != request_hash:
                    raise IdempotencyKeyReuseError("reused")
                return dict(row)
        return None

    async def add_request(self, values: dict[str, Any]):
        row = {
            "id": f"req-{len(self.requests) + 1}", "salon_id": values["salon_id"],
            "amount_paise": values["amount_paise"], "scheduled_for": values["scheduled_for"],
            "status": "requested", "reference": None, "reject_reason": None, "created_at": NOW,
            "processed_at": None, "cancelled_at": None, "idempotency_key": values["key"],
            "request_hash": values["hash"],
        }
        self.requests[row["id"]] = row
        return dict(row)

    async def get_request(self, request_id: str, *, salon_id=None, lock: bool = False):
        row = self.requests.get(request_id)
        if row is None or (salon_id is not None and row["salon_id"] != salon_id):
            return None
        return dict(row)

    async def cancel_request(self, request_id: str):
        row = self.requests[request_id]
        if row["status"] == "requested":
            row["status"] = "cancelled"
        return dict(row)

    async def finish_request(self, request_id: str, *, status: str, admin_id: str, reference, reject_reason):
        row = self.requests[request_id]
        if row["status"] == "requested":
            row.update(status=status, reference=reference, reject_reason=reject_reason)
        return dict(row)

    async def min_payout_paise(self):
        return self.minimum

    async def live_transfer(self, request_id: str):
        return self.live

    async def payout_account_for_request(self, request_id: str):
        if request_id not in self.requests or not self.account:
            return None
        return {"account_holder_name": "Asha", "upi_id": None, "bank_name": "Canara",
                "bank_account_number": "123456789012", "ifsc": "CNRB0001234",
                "changed_since_request": self.account_changed}

    async def queue(self, status, cursor, limit):
        rows = [
            {**row, "salon_name": "Glow", "account_holder_name": "Asha", "upi_id": "asha@upi",
             "bank_name": None, "bank_account_last4": None, "ifsc": None}
            for row in self.requests.values() if status is None or row["status"] == status
        ]
        return rows, None


def owner():
    return make_profile(id="owner-1", role=Role.owner)


def settle(repo: FakeWallet, request_id: str, reference: str = "UTR1") -> None:
    """A payout that was paid (the proof side is tested in test_payout_proof)."""

    repo.requests[request_id].update(status="paid", reference=reference)


def uc(repo: FakeWallet, live: bool = True) -> WalletUseCases:
    return WalletUseCases(repo, online_payments_live=live, clock=lambda: NOW)


async def ask(repo: FakeWallet, amount: int = 100_000, day: date = TODAY, key: str | None = KEY):
    return await uc(repo).request_payout(owner(), amount_paise=amount, scheduled_for=day, idempotency_key=key)


class TestAccess:
    @pytest.mark.parametrize("role", [Role.staff, Role.customer, Role.super_admin])
    async def test_only_the_owner_sees_the_wallet(self, role):
        with pytest.raises(ForbiddenError):
            await uc(FakeWallet()).summary(make_profile(role=role))

    async def test_a_salon_awaiting_approval_is_refused(self):
        repo = FakeWallet()
        repo.salon = {**SALON, "approval_status": "pending"}
        with pytest.raises(SalonApprovalRequiredError):
            await uc(repo).summary(owner())

    async def test_no_salon_is_refused(self):
        repo = FakeWallet()
        repo.salon = None
        with pytest.raises(ForbiddenError):
            await uc(repo).summary(owner())


class TestSummary:
    async def test_available_is_collected_less_commission(self):
        body = await uc(FakeWallet()).summary(owner())
        assert body["available_paise"] == 450_000
        assert body["requested_paise"] == 0 and body["paid_out_paise"] == 0
        assert body["min_payout_paise"] == MIN_PAYOUT_PAISE
        assert body["payout_account_ready"] is True and body["online_payments_live"] is True

    async def test_zero_and_flagged_while_online_payments_are_off(self):
        body = await uc(FakeWallet(collected=0, commission=0), live=False).summary(owner())
        assert body["available_paise"] == 0 and body["online_payments_live"] is False

    async def test_requested_and_paid_money_leaves_available(self):
        repo = FakeWallet()
        first = await ask(repo, 100_000, key="key-0000001")
        await ask(repo, 50_000, key="key-0000002")
        settle(repo, first["id"])
        body = await uc(repo).summary(owner())
        assert (body["available_paise"], body["requested_paise"], body["paid_out_paise"]) == (300_000, 50_000, 100_000)


class TestRequestPayout:
    async def test_creates_a_waiting_request_and_commits_under_the_lock(self):
        repo = FakeWallet()
        body = await ask(repo)
        assert body["status"] == "requested" and body["can_cancel"] is True and body["kind"] == "payout"
        assert body["amount_paise"] == 100_000 and body["scheduled_for"] == TODAY
        assert repo.commits == 1 and repo.locks == 1

    async def test_a_future_day_is_allowed(self):
        body = await ask(FakeWallet(), day=date(2026, 11, 9))
        assert body["scheduled_for"] == date(2026, 11, 9)

    async def test_key_is_required(self):
        with pytest.raises(IdempotencyKeyRequiredError):
            await ask(FakeWallet(), key=None)

    async def test_same_key_and_body_replays_without_a_second_request(self):
        repo = FakeWallet()
        first = await ask(repo)
        again = await ask(repo)
        assert again["id"] == first["id"] and len(repo.requests) == 1 and repo.commits == 1

    async def test_replay_still_works_after_the_balance_has_moved_on(self):
        repo = FakeWallet(collected=110_000, commission=0)
        first = await ask(repo, 100_000)
        assert (await ask(repo, 100_000))["id"] == first["id"]  # 10,000 left would refuse a new one

    async def test_same_key_with_a_different_amount_is_refused(self):
        repo = FakeWallet()
        await ask(repo, 100_000)
        with pytest.raises(IdempotencyKeyReuseError):
            await ask(repo, 120_000)

    async def test_more_than_available_is_refused(self):
        repo = FakeWallet()
        with pytest.raises(InsufficientBalanceError):
            await ask(repo, 450_001)
        assert not repo.requests

    async def test_two_requests_cannot_spend_the_same_balance(self):
        repo = FakeWallet()
        await ask(repo, 300_000, key="key-0000001")
        with pytest.raises(InsufficientBalanceError):
            await ask(repo, 200_000, key="key-0000002")

    async def test_the_whole_available_balance_can_be_asked_for(self):
        assert (await ask(FakeWallet(), 450_000))["amount_paise"] == 450_000

    async def test_below_the_minimum_is_refused(self):
        with pytest.raises(PayoutBelowMinimumError):
            await ask(FakeWallet(), MIN_PAYOUT_PAISE - 1)

    async def test_an_absurd_amount_is_refused(self):
        with pytest.raises(ValidationError):
            await ask(FakeWallet(), 10**12)

    async def test_a_past_day_is_refused(self):
        with pytest.raises(PayoutDayInvalidError):
            await ask(FakeWallet(), day=date(2026, 10, 31))

    async def test_today_is_the_salon_local_day_not_utc(self):
        late = datetime(2026, 11, 1, 19, 0, tzinfo=UTC)  # already 2 Nov 00:30 in India
        repo = FakeWallet()
        with pytest.raises(PayoutDayInvalidError):
            await WalletUseCases(repo, online_payments_live=True, clock=lambda: late).request_payout(
                owner(), amount_paise=100_000, scheduled_for=TODAY, idempotency_key=KEY
            )

    async def test_needs_a_payout_account(self):
        with pytest.raises(PayoutAccountMissingError):
            await ask(FakeWallet(account=False))

    async def test_staff_cannot_ask(self):
        with pytest.raises(ForbiddenError):
            await uc(FakeWallet()).request_payout(
                make_profile(role=Role.staff), amount_paise=100_000, scheduled_for=TODAY, idempotency_key=KEY
            )


class TestCancel:
    async def test_cancel_puts_the_money_back(self):
        repo = FakeWallet()
        made = await ask(repo, 400_000)
        done = await uc(repo).cancel_payout(owner(), made["id"])
        assert done["status"] == "cancelled" and done["can_cancel"] is False
        assert (await uc(repo).summary(owner()))["available_paise"] == 450_000

    async def test_cancelling_twice_is_safe(self):
        repo = FakeWallet()
        made = await ask(repo)
        await uc(repo).cancel_payout(owner(), made["id"])
        again = await uc(repo).cancel_payout(owner(), made["id"])
        assert again["status"] == "cancelled"

    async def test_a_paid_request_cannot_be_cancelled(self):
        repo = FakeWallet()
        made = await ask(repo)
        settle(repo, made["id"], "UTR9")
        with pytest.raises(PayoutNotCancellableError):
            await uc(repo).cancel_payout(owner(), made["id"])

    async def test_a_payout_already_on_its_way_through_cashfree_cannot_be_cancelled(self):
        repo = FakeWallet()
        made = await ask(repo)
        repo.live = {"id": "t1", "transfer_id": "po_1", "status": "pending"}
        with pytest.raises(PayoutTransferInProgressError):
            await uc(repo).cancel_payout(owner(), made["id"])
        assert repo.requests[made["id"]]["status"] == "requested"

    async def test_another_salons_request_is_not_found(self):
        repo = FakeWallet()
        made = await ask(repo)
        repo.requests[made["id"]]["salon_id"] = "salon-2"
        with pytest.raises(NotFoundError):
            await uc(repo).cancel_payout(owner(), made["id"])


class TestAdmin:
    async def test_only_a_super_admin_can_use_the_queue(self):
        repo = FakeWallet()
        made = await ask(repo)
        admin = WalletAdminUseCases(repo)
        for role in (Role.owner, Role.staff, Role.customer):
            actor = make_profile(role=role)
            with pytest.raises(ForbiddenError):
                await admin.list_requests(actor, status=None, cursor=None, limit=10)
            with pytest.raises(ForbiddenError):
                await admin.reject(actor, made["id"], "No reason")
            with pytest.raises(ForbiddenError):
                await admin.reveal_account(actor, made["id"])
        assert repo.requests[made["id"]]["status"] == "requested"

    async def test_a_waiting_request_reveals_the_full_account_to_the_admin(self):
        repo = FakeWallet()
        made = await ask(repo)
        account = await WalletAdminUseCases(repo).reveal_account(make_super_admin(), made["id"])
        assert account["bank_account_number"] == "123456789012" and account["ifsc"] == "CNRB0001234"

    async def test_the_admin_is_told_when_the_account_changed_after_the_request(self):
        repo = FakeWallet()
        made = await ask(repo)
        assert (await WalletAdminUseCases(repo).reveal_account(make_super_admin(), made["id"]))["changed_since_request"] is False
        repo.account_changed = True
        assert (await WalletAdminUseCases(repo).reveal_account(make_super_admin(), made["id"]))["changed_since_request"] is True

    async def test_the_account_is_not_revealed_once_the_request_is_handled(self):
        repo = FakeWallet()
        made = await ask(repo)
        admin = WalletAdminUseCases(repo)
        settle(repo, made["id"])
        with pytest.raises(PayoutAlreadyProcessedError):
            await admin.reveal_account(make_super_admin(), made["id"])

    async def test_revealing_an_unknown_request_or_a_missing_account_is_not_found(self):
        repo = FakeWallet()
        with pytest.raises(NotFoundError):
            await WalletAdminUseCases(repo).reveal_account(make_super_admin(), "missing")
        made = await ask(repo)
        repo.account = False
        with pytest.raises(NotFoundError):
            await WalletAdminUseCases(repo).reveal_account(make_super_admin(), made["id"])

    async def test_a_reveal_is_logged_without_the_account(self, caplog):
        repo = FakeWallet()
        made = await ask(repo)
        with caplog.at_level("INFO"):
            await WalletAdminUseCases(repo).reveal_account(make_super_admin(), made["id"])
        assert made["id"] in caplog.text and "123456789012" not in caplog.text

    async def test_queue_shows_the_masked_payout_account(self):
        repo = FakeWallet()
        await ask(repo)
        body = await WalletAdminUseCases(repo).list_requests(make_super_admin(), status="requested", cursor=None, limit=10)
        item = body["items"][0]
        assert item["salon_name"] == "Glow" and item["payout_account"]["upi_id"] == "asha@upi"
        assert "bank_account_number" not in item["payout_account"]

    async def test_unknown_status_filter_is_refused(self):
        with pytest.raises(ValidationError):
            await WalletAdminUseCases(FakeWallet()).list_requests(make_super_admin(), status="done", cursor=None, limit=10)

    async def test_reject_returns_the_money_with_a_reason(self):
        repo = FakeWallet()
        made = await ask(repo, 400_000)
        done = await WalletAdminUseCases(repo).reject(make_super_admin(), made["id"], "Account name did not match")
        assert done["status"] == "rejected" and done["reject_reason"] == "Account name did not match"
        assert (await uc(repo).summary(owner()))["available_paise"] == 450_000

    async def test_reject_needs_a_real_reason(self):
        repo = FakeWallet()
        made = await ask(repo)
        with pytest.raises(ValidationError):
            await WalletAdminUseCases(repo).reject(make_super_admin(), made["id"], "no")

    async def test_a_paid_request_cannot_be_rejected(self):
        repo = FakeWallet()
        made = await ask(repo)
        admin = WalletAdminUseCases(repo)
        settle(repo, made["id"], "1234")
        with pytest.raises(PayoutAlreadyProcessedError):
            await admin.reject(make_super_admin(), made["id"], "Changed my mind")

    async def test_unknown_request_is_not_found(self):
        with pytest.raises(NotFoundError):
            await WalletAdminUseCases(FakeWallet()).reject(make_super_admin(), "nope", "Not a known payout")


class TestMinimumPayout:
    async def test_the_admins_minimum_is_shown_and_enforced(self):
        repo = FakeWallet()
        repo.minimum = 50_000
        assert (await uc(repo).summary(owner()))["min_payout_paise"] == 50_000
        with pytest.raises(PayoutBelowMinimumError):
            await ask(repo, amount=49_999)
        assert (await ask(repo, amount=50_000))["status"] == "requested"

    async def test_without_a_setting_the_built_in_default_applies(self):
        repo = FakeWallet()
        assert (await uc(repo).summary(owner()))["min_payout_paise"] == MIN_PAYOUT_PAISE
