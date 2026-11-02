"""Paying a payout with proof: validation, the one-move rule, duplicates, corrections, audit and notices."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.use_cases.payout_proof import PayoutNotices, PayoutProofUseCases
from app.application.use_cases.wallet import WalletAdminUseCases
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PayoutAlreadyProcessedError,
    PayoutPaymentInvalidError,
    PayoutProofInvalidError,
    PayoutReferenceUsedError,
    ValidationError,
)
from app.domain.entities.profile import Role
from app.domain.services.payout_proof import (
    MAX_PROOF_BYTES,
    PaymentProblem,
    check_paid_at,
    check_proof,
    detect_proof_type,
)
from tests.conftest import make_profile, make_super_admin

NOW = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
ASKED = NOW - timedelta(hours=3)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64
BIG = PNG + b"0" * MAX_PROOF_BYTES
REQUEST = "req-1"


class FakeRepo:
    def __init__(self, amount: int = 100_000, status: str = "requested") -> None:
        self.row: dict[str, Any] = {
            "id": REQUEST, "salon_id": "salon-1", "amount_paise": amount, "scheduled_for": date(2026, 11, 2),
            "status": status, "reference": None, "reject_reason": None, "created_at": ASKED,
            "processed_at": None, "cancelled_at": None, "balance_snapshot": None,
            "salon_name": "Glow", "owner_name": "Asha", "account_holder_name": "Asha", "upi_id": "a@upi",
            "bank_name": None, "bank_account_last4": None, "ifsc": None,
        }
        self.payments: dict[str, dict[str, Any]] = {}
        self.proofs: dict[str, bytes] = {}
        self.corrections_list: list[dict[str, Any]] = []
        self.audits: list[tuple[str, str, str]] = []
        self.commits = 0
        self.duplicate_on_insert = False

    async def commit(self) -> None:
        self.commits += 1

    async def get_request(self, request_id, *, salon_id=None, lock=False):
        return dict(self.row) if request_id == REQUEST else None

    async def request_detail(self, request_id):
        return dict(self.row) if request_id == REQUEST else None

    async def reference_taken(self, reference):
        return any(p["reference"].lower() == reference.lower() for p in self.payments.values())

    async def add_proof(self, *, mime_type, content, sha256, admin_id):
        proof_id = f"proof-{len(self.proofs) + 1}"
        self.proofs[proof_id] = content
        assert len(sha256) == 64 and mime_type
        return proof_id

    async def add_payment(self, *, payout_id, reference, method, paid_at, amount_paid_paise,
                          adjustment_reason, note, proof_id, admin_id):
        if self.duplicate_on_insert:
            raise IntegrityError("insert", {}, Exception("duplicate"))
        self.payments[payout_id] = {
            "reference": reference, "method": method, "paid_at": paid_at, "amount_paid_paise": amount_paid_paise,
            "adjustment_reason": adjustment_reason, "note": note, "proof_id": proof_id,
            "proof_mime": "image/png", "proof_size": len(self.proofs[proof_id]),
        }

    async def payment(self, payout_id):
        return self.payments.get(payout_id)

    async def finish_request(self, request_id, *, status, admin_id, reference, reject_reason):
        if self.row["status"] == "requested":
            self.row.update(status=status, reference=reference, reject_reason=reject_reason, processed_at=NOW)
        return dict(self.row)

    async def audit(self, payout_id, action, admin_id):
        self.audits.append((payout_id, action, admin_id))

    async def audit_trail(self, payout_id):
        return [{"action": a, "created_at": NOW, "actor_name": "Admin"} for _, a, _ in self.audits]

    async def corrections(self, payout_id):
        return list(self.corrections_list)

    async def add_correction(self, *, payout_id, delta_paise, reason, reference, proof_id, admin_id):
        self.corrections_list.append({
            "id": f"c-{len(self.corrections_list) + 1}", "delta_paise": delta_paise, "reason": reason,
            "reference": reference, "created_at": NOW,
        })

    async def proof_file(self, payout_id):
        payment = self.payments.get(payout_id)
        return {"mime_type": "image/png", "content": memoryview(self.proofs[payment["proof_id"]])} if payment else None

    async def correction_proof_file(self, payout_id, correction_id):
        return None

    async def owner_id_of_salon(self, salon_id):
        return "owner-1"

    async def reconciliation(self, start, end, timezone):
        return [
            {"day": date(2026, 11, 2), "kind": "requested", "count": 2, "amount_paise": 300_000, "asked_paise": 300_000},
            {"day": date(2026, 11, 2), "kind": "paid", "count": 1, "amount_paise": 95_000, "asked_paise": 100_000},
        ]


def pay_args(**over: Any) -> dict[str, Any]:
    base = {
        "reference": "UTR123", "method": "upi", "paid_at": NOW - timedelta(minutes=5),
        "amount_paid_paise": 100_000, "adjustment_reason": None, "note": None, "proof": PNG,
    }
    return {**base, **over}


def uc(repo: FakeRepo, notices: PayoutNotices | None = None) -> PayoutProofUseCases:
    return PayoutProofUseCases(repo, notices=notices, clock=lambda: NOW)


class TestFileRules:
    def test_the_real_file_type_is_read_from_its_first_bytes(self):
        assert detect_proof_type(PNG) == "image/png"
        assert detect_proof_type(b"\xff\xd8\xff\xe0" + b"0" * 10) == "image/jpeg"
        assert detect_proof_type(b"RIFF1234WEBPVP8 ") == "image/webp"
        assert detect_proof_type(PDF) == "application/pdf"
        assert detect_proof_type(b"MZ\x90\x00 an exe renamed .png") is None

    @pytest.mark.parametrize("data", [b"", b"just text", BIG], ids=["empty", "text", "oversized"])
    def test_empty_oversized_or_other_files_are_refused(self, data):
        with pytest.raises(PaymentProblem):
            check_proof(data)

    def test_paid_at_must_have_a_zone_not_be_future_and_not_precede_the_request(self):
        with pytest.raises(PaymentProblem):
            check_paid_at(datetime(2026, 11, 2, 9, 0), requested_at=ASKED, now=NOW)
        with pytest.raises(PaymentProblem):
            check_paid_at(NOW + timedelta(hours=1), requested_at=ASKED, now=NOW)
        with pytest.raises(PaymentProblem):
            check_paid_at(ASKED - timedelta(minutes=1), requested_at=ASKED, now=NOW)
        assert check_paid_at(NOW + timedelta(minutes=2), requested_at=ASKED, now=NOW)  # clock skew


class TestPay:
    async def test_pays_with_proof_and_records_everything_in_one_commit(self):
        repo = FakeRepo()
        done = await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(reference="  UTR123  "))
        assert done["status"] == "paid" and done["reference"] == "UTR123" and done["method"] == "upi"
        assert repo.payments[REQUEST]["amount_paid_paise"] == 100_000 and len(repo.proofs) == 1
        assert repo.audits == [(REQUEST, "pay", "admin-001")] and repo.commits == 1

    @pytest.mark.parametrize("role", [Role.owner, Role.staff, Role.customer])
    async def test_only_a_super_admin_can_pay(self, role):
        repo = FakeRepo()
        with pytest.raises(ForbiddenError):
            await uc(repo).pay(make_profile(role=role), REQUEST, **pay_args())
        assert not repo.payments

    @pytest.mark.parametrize("proof", [b"", b"not an image", BIG], ids=["empty", "text", "oversized"])
    async def test_no_proof_means_no_payment(self, proof):
        repo = FakeRepo()
        with pytest.raises(PayoutProofInvalidError):
            await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(proof=proof))
        assert repo.row["status"] == "requested" and not repo.payments and not repo.proofs

    @pytest.mark.parametrize("override", [
        {"reference": ""}, {"reference": "   "}, {"reference": "x" * 101}, {"method": "cheque"},
        {"amount_paid_paise": 0}, {"paid_at": NOW + timedelta(days=1)}, {"paid_at": ASKED - timedelta(hours=1)},
        {"note": "n" * 201},
    ])
    async def test_bad_payment_details_are_refused(self, override):
        repo = FakeRepo()
        with pytest.raises(PayoutPaymentInvalidError):
            await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(**override))
        assert repo.row["status"] == "requested" and not repo.proofs

    async def test_a_different_amount_needs_a_written_reason(self):
        repo = FakeRepo()
        with pytest.raises(PayoutPaymentInvalidError):
            await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(amount_paid_paise=95_000))
        done = await uc(repo).pay(
            make_super_admin(), REQUEST, **pay_args(amount_paid_paise=95_000, adjustment_reason="Bank fee kept")
        )
        assert done["status"] == "paid" and repo.payments[REQUEST]["adjustment_reason"] == "Bank fee kept"

    async def test_a_reason_is_not_kept_when_the_amount_matches(self):
        repo = FakeRepo()
        await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(adjustment_reason="not needed"))
        assert repo.payments[REQUEST]["adjustment_reason"] is None

    async def test_a_reference_used_before_is_refused(self):
        repo = FakeRepo()
        repo.payments["other"] = {"reference": "utr123"}
        with pytest.raises(PayoutReferenceUsedError):
            await uc(repo).pay(make_super_admin(), REQUEST, **pay_args())
        assert repo.row["status"] == "requested" and not repo.proofs

    async def test_a_race_on_the_unique_reference_becomes_the_same_refusal(self):
        repo = FakeRepo()
        repo.duplicate_on_insert = True
        with pytest.raises(PayoutReferenceUsedError):
            await uc(repo).pay(make_super_admin(), REQUEST, **pay_args())
        assert repo.commits == 0

    async def test_retrying_the_same_payment_returns_it_without_a_second_record(self):
        repo = FakeRepo()
        first = await uc(repo).pay(make_super_admin(), REQUEST, **pay_args())
        again = await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(reference="utr123"))
        assert again["id"] == first["id"] and len(repo.proofs) == 1 and repo.commits == 1

    async def test_a_paid_payout_cannot_be_paid_again_with_another_reference(self):
        repo = FakeRepo()
        await uc(repo).pay(make_super_admin(), REQUEST, **pay_args())
        with pytest.raises(PayoutAlreadyProcessedError):
            await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(reference="UTR999"))
        assert repo.payments[REQUEST]["reference"] == "UTR123"

    @pytest.mark.parametrize("status", ["rejected", "cancelled"])
    async def test_a_handled_request_cannot_be_paid(self, status):
        repo = FakeRepo(status=status)
        with pytest.raises(PayoutAlreadyProcessedError):
            await uc(repo).pay(make_super_admin(), REQUEST, **pay_args())

    async def test_unknown_request_is_not_found(self):
        with pytest.raises(NotFoundError):
            await uc(FakeRepo()).pay(make_super_admin(), "missing", **pay_args())

    async def test_the_owner_is_told_after_the_payment_and_a_failed_push_changes_nothing(self):
        sent: list[dict[str, Any]] = []

        async def notify(**kwargs):
            sent.append(kwargs)

        repo = FakeRepo()
        await uc(repo, PayoutNotices(notify, repo.owner_id_of_salon)).pay(make_super_admin(), REQUEST, **pay_args())
        assert sent[0]["user_id"] == "owner-1" and "UTR123" in sent[0]["body"] and "₹1,000.00" in sent[0]["body"]

        async def broken(**kwargs):
            raise RuntimeError("fcm down")

        repo2 = FakeRepo()
        done = await uc(repo2, PayoutNotices(broken, repo2.owner_id_of_salon)).pay(
            make_super_admin(), REQUEST, **pay_args()
        )
        assert done["status"] == "paid"


class TestDetailProofAndCorrection:
    async def test_detail_shows_payment_timeline_and_proof_info_but_no_file(self):
        repo = FakeRepo()
        await uc(repo).pay(make_super_admin(), REQUEST, **pay_args(note="Paid via HDFC"))
        body = await uc(repo).detail(make_super_admin(), REQUEST)
        assert body["salon_name"] == "Glow" and body["payment"]["reference"] == "UTR123"
        assert body["payment"]["proof_mime"] == "image/png" and "content" not in body["payment"]
        assert body["timeline"][0]["action"] == "pay" and body["method"] == "upi"

    async def test_viewing_the_proof_returns_the_file_and_is_audited(self):
        repo = FakeRepo()
        await uc(repo).pay(make_super_admin(), REQUEST, **pay_args())
        file = await uc(repo).proof(make_super_admin(), REQUEST)
        assert file["content"] == PNG and file["mime_type"] == "image/png"
        assert repo.audits[-1][1] == "view_proof"

    async def test_no_proof_is_not_found_and_other_roles_are_refused(self):
        repo = FakeRepo()
        with pytest.raises(NotFoundError):
            await uc(repo).proof(make_super_admin(), REQUEST)
        with pytest.raises(ForbiddenError):
            await uc(repo).proof(make_profile(role=Role.owner), REQUEST)
        with pytest.raises(ForbiddenError):
            await uc(repo).detail(make_profile(role=Role.staff), REQUEST)

    async def test_a_correction_needs_a_paid_payout_a_reason_and_proof(self):
        repo = FakeRepo()
        args = {"delta_paise": 5_000, "reason": "Paid 50 too little", "reference": "UTR124", "proof": PDF}
        with pytest.raises(ConflictError):
            await uc(repo).correct(make_super_admin(), REQUEST, **args)
        await uc(repo).pay(make_super_admin(), REQUEST, **pay_args())
        with pytest.raises(PayoutPaymentInvalidError):
            await uc(repo).correct(make_super_admin(), REQUEST, **{**args, "delta_paise": 0})
        with pytest.raises(PayoutPaymentInvalidError):
            await uc(repo).correct(make_super_admin(), REQUEST, **{**args, "reason": "  "})
        with pytest.raises(PayoutProofInvalidError):
            await uc(repo).correct(make_super_admin(), REQUEST, **{**args, "proof": b"nope"})
        body = await uc(repo).correct(make_super_admin(), REQUEST, **args)
        assert body["corrections"][0]["delta_paise"] == 5_000
        assert body["payment"]["amount_paid_paise"] == 100_000  # the paid record itself is untouched
        assert repo.audits[-1][1] == "correct"


class TestReconciliationAndWalletHooks:
    async def test_days_without_activity_are_zero_and_the_difference_is_paid_less_asked(self):
        body = await uc(FakeRepo()).reconciliation(make_super_admin(), date(2026, 11, 1), date(2026, 11, 2))
        first, second = body["items"]
        assert first["date"] == date(2026, 11, 1) and first["paid_paise"] == 0
        assert second["requested_paise"] == 300_000 and second["difference_paise"] == -5_000
        assert body["totals"]["paid_paise"] == 95_000 and body["totals"]["difference_paise"] == -5_000

    async def test_a_backwards_or_huge_range_is_refused(self):
        with pytest.raises(ValidationError):
            await uc(FakeRepo()).reconciliation(make_super_admin(), date(2026, 11, 2), date(2026, 11, 1))
        with pytest.raises(ValidationError):
            await uc(FakeRepo()).reconciliation(make_super_admin(), date(2026, 1, 1), date(2026, 11, 1))
        with pytest.raises(ForbiddenError):
            await uc(FakeRepo()).reconciliation(make_profile(role=Role.owner), date(2026, 11, 1), date(2026, 11, 2))

    async def test_a_reveal_and_a_decline_are_audited_and_the_owner_is_told(self):
        repo = FakeRepo()
        sent: list[dict[str, Any]] = []

        async def notify(**kwargs):
            sent.append(kwargs)

        async def account(_request_id):
            return {"account_holder_name": "A", "upi_id": "a@upi", "bank_name": None,
                    "bank_account_number": None, "ifsc": None}

        repo.payout_account_for_request = account  # type: ignore[attr-defined]
        admin = WalletAdminUseCases(repo, audit=repo.audit, notices=PayoutNotices(notify, repo.owner_id_of_salon))
        await admin.reveal_account(make_super_admin(), REQUEST)
        await admin.reject(make_super_admin(), REQUEST, "Account name did not match")
        assert [a for _, a, _ in repo.audits] == ["reveal", "decline"]
        assert sent[0]["title"] == "Payout declined" and "Account name did not match" in sent[0]["body"]
