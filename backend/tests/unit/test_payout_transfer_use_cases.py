"""Automatic payout use cases against in-memory fakes: the money-safety rules, not the provider."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.ports.payout_transfer import (
    BeneficiaryRequest,
    PayoutTransferGateway,
    TransferRequest,
    TransferResult,
)
from app.application.use_cases.payout_transfer import PayoutTransferUseCases
from app.core.exceptions import (
    ForbiddenError,
    NotFoundError,
    PayoutAlreadyProcessedError,
    PayoutOutcomeUnknownError,
    PayoutProviderError,
    PayoutProviderUnavailableError,
    PayoutTransferInProgressError,
    PayoutTransferInvalidError,
)
from tests.conftest import make_profile, make_super_admin

NOW = datetime(2026, 11, 12, 6, 30, tzinfo=UTC)
REQUEST = "0b3f2c1a-7d4e-4a55-9f60-1c2d3e4f5a6b"
SALON = "5c9a1e00-1111-4222-8333-444455556666"
ADMIN = make_super_admin()


class Events(list):
    """The order things happened in, shared by the fakes."""


class FakeRepo:
    def __init__(self, events: Events, *, amount: int = 25_000) -> None:
        self.events = events
        self.request = {"id": REQUEST, "salon_id": SALON, "amount_paise": amount, "status": "requested",
                        "reference": None}
        self.account: dict[str, Any] | None = {
            "account_holder_name": "Asha R", "upi_id": None, "bank_name": "HDFC",
            "bank_account_number": "123456789012", "ifsc": "HDFC0000001",
        }
        self.contact: dict[str, Any] | None = {"full_name": "Asha R", "phone": "+91 98765 43210"}
        self.rows: list[dict[str, Any]] = []
        self.payments: list[dict[str, Any]] = []
        self.audits: list[tuple[str, str | None]] = []
        self.used_references: set[str] = set()

    async def commit(self) -> None:
        self.events.append("commit")

    async def get_request(self, request_id, *, salon_id=None, lock=False):
        return dict(self.request) if request_id == REQUEST else None

    async def live_transfer(self, request_id):
        return next((dict(r) for r in self.rows if r["status"] in ("pending", "success")), None)

    async def payout_account_for_request(self, request_id):
        return dict(self.account) if self.account else None

    async def owner_contact(self, salon_id):
        return self.contact

    async def transfers(self, request_id):
        return [dict(r) for r in self.rows]

    async def add_transfer(self, *, request_id, transfer_id, beneficiary_id, mode, amount_paise, admin_id):
        row = {"id": f"t{len(self.rows) + 1}", "request_id": request_id, "transfer_id": transfer_id,
               "beneficiary_id": beneficiary_id, "mode": mode, "amount_paise": amount_paise, "status": "pending",
               "provider_status": None, "cf_transfer_id": None, "utr": None, "failure_reason": None,
               "created_at": NOW, "updated_at": NOW}
        self.rows.append(row)
        self.events.append("row_added")
        return dict(row)

    async def transfer_by_provider_id(self, transfer_id, *, lock=False):
        row = next((r for r in self.rows if r["transfer_id"] == transfer_id), None)
        return dict(row) if row else None

    async def update_transfer(self, transfer_id, *, status, provider_status, cf_transfer_id, utr, failure_reason):
        row = next(r for r in self.rows if r["transfer_id"] == transfer_id)
        row.update(status=status)
        for key, value in (("provider_status", provider_status), ("cf_transfer_id", cf_transfer_id),
                           ("utr", utr), ("failure_reason", failure_reason)):
            if value is not None:
                row[key] = value
        return dict(row)

    async def reference_taken(self, reference):
        return reference in self.used_references

    async def add_provider_payment(self, *, payout_id, reference, method, amount_paise, transfer_id):
        self.payments.append({"payout_id": payout_id, "reference": reference, "method": method,
                              "amount_paise": amount_paise, "transfer_id": transfer_id})

    async def finish_request(self, request_id, *, status, admin_id, reference, reject_reason):
        if self.request["status"] == "requested":
            self.request.update(status=status, reference=reference)
        return dict(self.request)

    async def audit(self, payout_id, action, admin_id):
        self.audits.append((action, admin_id))


class FakeGateway(PayoutTransferGateway):
    provider_name = "fake"

    def __init__(self, events: Events) -> None:
        self.events = events
        self.beneficiary_error: Exception | None = None
        self.create_outcome: Any = TransferResult(transfer_id="", status="RECEIVED")
        self.lookup_outcome: Any = None
        self.created: list[TransferRequest] = []
        self.beneficiaries: list[BeneficiaryRequest] = []

    async def upsert_beneficiary(self, beneficiary):
        self.events.append("beneficiary")
        if self.beneficiary_error:
            raise self.beneficiary_error
        self.beneficiaries.append(beneficiary)

    async def create_transfer(self, request):
        self.events.append("create_transfer")
        self.created.append(request)
        if isinstance(self.create_outcome, Exception):
            raise self.create_outcome
        return TransferResult(transfer_id=request.transfer_id, status=self.create_outcome.status,
                              cf_transfer_id=self.create_outcome.cf_transfer_id, utr=self.create_outcome.utr,
                              status_code=self.create_outcome.status_code)

    async def get_transfer(self, transfer_id):
        self.events.append("lookup")
        if isinstance(self.lookup_outcome, Exception):
            raise self.lookup_outcome
        if self.lookup_outcome is None:
            return None
        return TransferResult(transfer_id=transfer_id, status=self.lookup_outcome.status,
                              utr=self.lookup_outcome.utr, cf_transfer_id=self.lookup_outcome.cf_transfer_id,
                              status_code=self.lookup_outcome.status_code)

    def verify_webhook_signature(self, raw_body, headers):
        return True

    def parse_webhook(self, raw_body):
        return None


class Notices:
    def __init__(self) -> None:
        self.paid_calls: list[tuple] = []

    async def paid(self, salon_id, payout_id, amount_paise, reference):
        self.paid_calls.append((salon_id, payout_id, amount_paise, reference))


@pytest.fixture
def world():
    events = Events()
    repo, gateway, notices = FakeRepo(events), FakeGateway(events), Notices()
    uc = PayoutTransferUseCases(repo, gateway, notices=notices)
    return uc, repo, gateway, notices, events


def result(status: str, **kw) -> TransferResult:
    return TransferResult(transfer_id=kw.pop("transfer_id", ""), status=status, **kw)


# ------------------------------------------------------------------- send
class TestSend:
    async def test_the_pending_row_is_committed_before_the_provider_is_asked_to_move_money(self, world):
        uc, repo, _gateway, _, events = world
        await uc.send(ADMIN, REQUEST)

        assert events.index("beneficiary") < events.index("row_added") < events.index("commit")
        assert events.index("commit") < events.index("create_transfer")
        assert [r["status"] for r in repo.rows] == ["pending"]
        assert repo.request["status"] == "requested"  # still waiting until the provider says SUCCESS
        assert ("send_transfer", ADMIN.id) in repo.audits

    async def test_it_sends_by_imps_to_the_bank_account_with_the_owner_phone_and_a_stable_beneficiary(self, world):
        uc, _repo, gateway, _, _ = world
        await uc.send(ADMIN, REQUEST)

        beneficiary = gateway.beneficiaries[0]
        assert (beneficiary.mode, beneficiary.ifsc, beneficiary.phone) == ("imps", "HDFC0000001", "9876543210")
        assert gateway.created[0].amount_paise == 25_000 and gateway.created[0].mode == "imps"
        assert gateway.created[0].transfer_id.endswith("_1")

    async def test_a_success_reply_pays_the_request_without_a_proof_file_and_tells_the_owner(self, world):
        uc, repo, gateway, notices, _ = world
        gateway.create_outcome = result("SUCCESS", utr="UTR123456")
        await uc.send(ADMIN, REQUEST)

        assert repo.request["status"] == "paid" and repo.request["reference"] == "UTR123456"
        assert repo.payments == [{"payout_id": REQUEST, "reference": "UTR123456", "method": "imps",
                                  "amount_paise": 25_000, "transfer_id": repo.rows[0]["transfer_id"]}]
        assert notices.paid_calls == [(SALON, REQUEST, 25_000, "UTR123456")]
        assert ("transfer_success", ADMIN.id) in repo.audits

    async def test_a_reused_utr_falls_back_to_the_transfer_id_as_the_reference(self, world):
        uc, repo, gateway, _, _ = world
        repo.used_references.add("UTR-DUP")
        gateway.create_outcome = result("SUCCESS", utr="UTR-DUP")
        await uc.send(ADMIN, REQUEST)
        assert repo.request["reference"] == repo.rows[0]["transfer_id"]

    async def test_only_the_super_admin_can_send(self, world):
        uc, repo, gateway, _, _ = world
        with pytest.raises(ForbiddenError):
            await uc.send(make_profile(id="owner-1"), REQUEST)
        assert repo.rows == [] and gateway.created == []

    async def test_a_request_already_handled_or_with_a_live_transfer_is_refused(self, world):
        uc, repo, gateway, _, _ = world
        repo.request["status"] = "paid"
        with pytest.raises(PayoutAlreadyProcessedError):
            await uc.send(ADMIN, REQUEST)
        repo.request["status"] = "requested"
        await uc.send(ADMIN, REQUEST)
        with pytest.raises(PayoutTransferInProgressError):
            await uc.send(ADMIN, REQUEST)
        assert len(gateway.created) == 1  # never a second transfer for one request

    async def test_unknown_request_and_missing_provider(self, world):
        uc, repo, _, _, _ = world
        with pytest.raises(NotFoundError):
            await uc.send(ADMIN, "00000000-0000-0000-0000-000000000000")
        with pytest.raises(PayoutProviderUnavailableError):
            await PayoutTransferUseCases(repo, None).send(ADMIN, REQUEST)

    @pytest.mark.parametrize("break_it", ["no_account", "no_phone", "no_instrument", "too_large"])
    async def test_an_account_that_cannot_be_paid_stores_nothing_and_calls_no_provider(self, world, break_it):
        uc, repo, gateway, _, _ = world
        if break_it == "no_account":
            repo.account = None
        elif break_it == "no_phone":
            repo.contact = {"full_name": "A", "phone": None}
        elif break_it == "no_instrument":
            repo.account.update(bank_account_number=None, ifsc=None)
        else:
            repo.request["amount_paise"] = 6_00_000_00
        with pytest.raises(PayoutTransferInvalidError):
            await uc.send(ADMIN, REQUEST)
        assert repo.rows == [] and gateway.beneficiaries == [] and gateway.created == []

    async def test_a_beneficiary_refusal_happens_before_any_transfer_exists(self, world):
        uc, repo, gateway, _, _ = world
        gateway.beneficiary_error = PayoutProviderError("no", {"provider_code": "bank_ifsc_invalid"})
        with pytest.raises(PayoutProviderError):
            await uc.send(ADMIN, REQUEST)
        assert repo.rows == [] and gateway.created == []


# ------------------------------------------------------- uncertain outcomes
class TestUncertainOutcomes:
    async def test_a_timeout_then_a_lookup_that_finds_success_pays_without_sending_again(self, world):
        uc, repo, gateway, _, _ = world
        gateway.create_outcome = PayoutOutcomeUnknownError("timeout")
        gateway.lookup_outcome = result("SUCCESS", utr="UTR-LATE")
        await uc.send(ADMIN, REQUEST)

        assert len(gateway.created) == 1 and repo.request["status"] == "paid"

    async def test_a_timeout_with_no_record_yet_stays_pending_and_is_never_marked_failed(self, world):
        uc, repo, gateway, _, _ = world
        gateway.create_outcome = PayoutOutcomeUnknownError("timeout")
        gateway.lookup_outcome = None
        await uc.send(ADMIN, REQUEST)

        assert repo.rows[0]["status"] == "pending" and repo.request["status"] == "requested"
        assert all(action != "transfer_failed" for action, _ in repo.audits)

    async def test_a_timeout_and_a_failed_lookup_also_stay_pending(self, world):
        uc, repo, gateway, _, _ = world
        gateway.create_outcome = PayoutOutcomeUnknownError("timeout")
        gateway.lookup_outcome = PayoutOutcomeUnknownError("still down")
        await uc.send(ADMIN, REQUEST)
        assert repo.rows[0]["status"] == "pending"

    async def test_a_definite_refusal_marks_that_transfer_failed_and_leaves_the_request_waiting(self, world):
        uc, repo, gateway, _, _ = world
        gateway.create_outcome = PayoutProviderError("no", {"provider_code": "insufficient_balance"})
        with pytest.raises(PayoutProviderError) as caught:
            await uc.send(ADMIN, REQUEST)

        assert repo.rows[0]["status"] == "failed" and repo.rows[0]["failure_reason"] == "insufficient_balance"
        # Only our own short code goes back to the admin, not the provider's answer.
        assert caught.value.details == {"failure_reason": "insufficient_balance"}
        assert repo.request["status"] == "requested" and repo.payments == []

    async def test_a_refusal_is_not_proof_the_provider_holds_no_transfer_so_it_is_looked_up_first(self, world):
        """A provider may answer a duplicate with a 4xx: never record 'failed' on that alone."""

        uc, repo, gateway, _notices, _ = world
        gateway.create_outcome = PayoutProviderError("no", {"provider_code": "request_invalid"})
        gateway.lookup_outcome = result("SUCCESS", utr="U-DUP")
        await uc.send(ADMIN, REQUEST)  # no error: the transfer exists, so it is applied, not failed

        assert repo.request["status"] == "paid" and repo.rows[0]["status"] == "success"
        assert all(action != "transfer_failed" for action, _ in repo.audits)

    async def test_a_refusal_with_an_unreachable_lookup_stays_pending_not_failed(self, world):
        uc, repo, gateway, _, _ = world
        gateway.create_outcome = PayoutProviderError("no", {"provider_code": "request_invalid"})
        gateway.lookup_outcome = PayoutOutcomeUnknownError("down")
        await uc.send(ADMIN, REQUEST)
        assert repo.rows[0]["status"] == "pending" and repo.request["status"] == "requested"

    async def test_every_earlier_failed_attempt_is_looked_up_not_only_the_last(self, world):
        uc, repo, gateway, _, _ = world
        for _ in range(2):  # two attempts recorded as failed
            gateway.create_outcome = PayoutProviderError("no", {"provider_code": "x"})
            with pytest.raises(PayoutProviderError):
                await uc.send(ADMIN, REQUEST)
        first_id = repo.rows[0]["transfer_id"]
        gateway.create_outcome = result("RECEIVED")

        async def only_the_first_succeeded(transfer_id):
            if transfer_id == first_id:
                return result("SUCCESS", transfer_id=transfer_id, utr="U-FIRST")
            return result("FAILED", transfer_id=transfer_id)

        gateway.get_transfer = only_the_first_succeeded
        with pytest.raises(PayoutTransferInProgressError):
            await uc.send(ADMIN, REQUEST)
        assert len(repo.rows) == 2 and repo.request["status"] == "paid"  # no third transfer, and the hidden success paid it

    async def test_an_account_changed_after_the_request_is_not_paid_automatically(self, world):
        uc, repo, gateway, _, _ = world
        repo.account["changed_since_request"] = True
        with pytest.raises(PayoutTransferInvalidError, match="changed their payout account"):
            await uc.send(ADMIN, REQUEST)
        assert repo.rows == [] and gateway.beneficiaries == [] and gateway.created == []

    async def test_after_a_failure_the_admin_can_send_again_as_a_new_attempt(self, world):
        uc, repo, gateway, _, _ = world
        gateway.create_outcome = PayoutProviderError("no", {"provider_code": "x"})
        with pytest.raises(PayoutProviderError):
            await uc.send(ADMIN, REQUEST)
        gateway.create_outcome = result("RECEIVED")
        await uc.send(ADMIN, REQUEST)

        assert [r["transfer_id"][-2:] for r in repo.rows] == ["_1", "_2"]
        assert [r["status"] for r in repo.rows] == ["failed", "pending"]


# ------------------------------------------------------- refresh and webhook
class TestFollowingTheTransfer:
    async def test_refresh_pays_the_request_when_the_provider_reports_success(self, world):
        uc, repo, gateway, _, _ = world
        await uc.send(ADMIN, REQUEST)
        gateway.lookup_outcome = result("SUCCESS", utr="UTR-R")
        await uc.refresh(ADMIN, REQUEST)
        assert repo.request["status"] == "paid" and repo.payments[0]["reference"] == "UTR-R"

    async def test_refresh_with_no_provider_record_submits_the_same_transfer_id_not_a_new_one(self, world):
        uc, repo, gateway, _, _ = world
        gateway.create_outcome = PayoutOutcomeUnknownError("timeout")
        await uc.send(ADMIN, REQUEST)
        first_id = repo.rows[0]["transfer_id"]
        gateway.create_outcome = result("RECEIVED")
        gateway.lookup_outcome = None
        await uc.refresh(ADMIN, REQUEST)

        assert [c.transfer_id for c in gateway.created] == [first_id, first_id]
        assert len(repo.rows) == 1

    async def test_refresh_of_a_failed_report_leaves_the_request_waiting(self, world):
        uc, repo, gateway, _, _ = world
        await uc.send(ADMIN, REQUEST)
        gateway.lookup_outcome = result("FAILED", status_code="INVALID_BENE_ACCOUNT_OR_IFSC")
        await uc.refresh(ADMIN, REQUEST)
        assert repo.rows[0]["status"] == "failed"
        assert repo.rows[0]["failure_reason"] == "INVALID_BENE_ACCOUNT_OR_IFSC"
        assert repo.request["status"] == "requested" and repo.payments == []

    async def test_a_repeated_success_event_pays_once(self, world):
        uc, repo, _, notices, _ = world
        await uc.send(ADMIN, REQUEST)
        transfer_id = repo.rows[0]["transfer_id"]
        for _ in range(3):
            await uc.apply(result("SUCCESS", transfer_id=transfer_id, utr="UTR-ONCE"), admin_id=None)

        assert len(repo.payments) == 1 and len(notices.paid_calls) == 1

    async def test_a_bank_reversal_after_success_is_recorded_but_does_not_touch_the_wallet(self, world):
        uc, repo, _, _, _ = world
        await uc.send(ADMIN, REQUEST)
        transfer_id = repo.rows[0]["transfer_id"]
        await uc.apply(result("SUCCESS", transfer_id=transfer_id, utr="U1"), admin_id=None)
        await uc.apply(result("REVERSED", transfer_id=transfer_id), admin_id=None)

        assert repo.rows[0]["status"] == "reversed"
        assert repo.request["status"] == "paid"  # the admin reviews it and records a correction
        assert ("transfer_reversed", None) in repo.audits

    async def test_a_late_success_after_a_recorded_failure_still_pays_the_request(self, world):
        """The provider is the source of truth: money that went out must be reflected, not ignored."""

        uc, repo, _, notices, _ = world
        await uc.send(ADMIN, REQUEST)
        transfer_id = repo.rows[0]["transfer_id"]
        await uc.apply(result("FAILED", transfer_id=transfer_id), admin_id=None)
        await uc.apply(result("SUCCESS", transfer_id=transfer_id, utr="U9"), admin_id=None)

        assert repo.rows[0]["status"] == "success" and repo.request["status"] == "paid"
        assert len(repo.payments) == 1 and len(notices.paid_calls) == 1

    async def test_success_for_a_request_that_was_already_handled_is_flagged_not_paid_twice_and_never_raises(self, world):
        uc, repo, _, notices, _ = world
        await uc.send(ADMIN, REQUEST)
        transfer_id = repo.rows[0]["transfer_id"]
        await uc.apply(result("FAILED", transfer_id=transfer_id), admin_id=None)
        repo.request["status"] = "paid"  # the admin paid it by hand after the failure
        await uc.apply(result("SUCCESS", transfer_id=transfer_id, utr="U9"), admin_id=None)

        assert repo.payments == [] and notices.paid_calls == []
        assert ("transfer_conflict", None) in repo.audits

    async def test_before_a_new_attempt_the_failed_one_is_looked_up_and_a_hidden_success_blocks_the_resend(self, world):
        uc, repo, gateway, _, _ = world
        await uc.send(ADMIN, REQUEST)
        await uc.apply(result("FAILED", transfer_id=repo.rows[0]["transfer_id"]), admin_id=None)
        gateway.lookup_outcome = result("SUCCESS", utr="U-HIDDEN")

        with pytest.raises(PayoutTransferInProgressError):
            await uc.send(ADMIN, REQUEST)

        assert len(gateway.created) == 1 and len(repo.rows) == 1  # never a second transfer
        assert repo.request["status"] == "paid"  # and the hidden success was applied

    async def test_a_confirmed_failure_does_not_block_the_next_attempt(self, world):
        uc, repo, gateway, _, _ = world
        await uc.send(ADMIN, REQUEST)
        await uc.apply(result("FAILED", transfer_id=repo.rows[0]["transfer_id"]), admin_id=None)
        gateway.lookup_outcome = result("FAILED")
        await uc.send(ADMIN, REQUEST)
        assert len(repo.rows) == 2

    async def test_an_event_for_an_unknown_transfer_is_ignored(self, world):
        uc, repo, _, _, _ = world
        await uc.apply(result("SUCCESS", transfer_id="po_unknown_1"), admin_id=None)
        assert repo.payments == [] and repo.request["status"] == "requested"

    async def test_an_in_flight_status_keeps_the_transfer_pending(self, world):
        uc, repo, _, _, _ = world
        await uc.send(ADMIN, REQUEST)
        await uc.apply(result("QUEUED", transfer_id=repo.rows[0]["transfer_id"]), admin_id=None)
        assert repo.rows[0]["status"] == "pending" and repo.rows[0]["provider_status"] == "QUEUED"

    async def test_refresh_without_a_started_transfer_is_not_found(self, world):
        uc, _, _, _, _ = world
        with pytest.raises(NotFoundError):
            await uc.refresh(ADMIN, REQUEST)
