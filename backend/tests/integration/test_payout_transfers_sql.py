"""Automatic payout transfers (0068) on the real prepared schema (0038..0068).

The money-safety rules live in the database: one live transfer per request, no cancel / reject /
by-hand payment while a transfer is live, no proof needed for a provider-sent payment, and salon
erasure still works. Opt-in like the other SQL suites: MIGRATION_TEST_DB.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration import salon_erasure_support as support
from tests.integration.test_payment_ledger_sql import TEST_DB

env = support.env
prepared_db = support.prepared_db

pytestmark = [
    pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL"),
    pytest.mark.parametrize("prepared_db", [68], indirect=True, scope="module"),
]

AMOUNT = 25_000


async def _request(env, f, amount=AMOUNT):
    return (await env.sql(
        """insert into salon_payout_requests(salon_id, amount_paise, scheduled_for, idempotency_key, request_hash)
           values(:s, :a, current_date, :k, repeat('a', 64)) returning id""",
        s=f["salon"], a=amount, k="payout-" + uuid4().hex))[0]["id"]


async def _transfer(env, request_id, *, amount=AMOUNT, attempt=1, mode="imps"):
    return (await env.sql(
        """insert into salon_payout_transfers(request_id, transfer_id, beneficiary_id, mode, amount_paise)
           values(:r, :t, 'bene_1', :m, :a) returning id""",
        r=request_id, t=f"po_{uuid4().hex}_{attempt}", m=mode, a=amount))[0]["id"]


async def _status(env, table, row_id):
    return (await env.sql(f"select status from {table} where id = :i", i=row_id))[0]["status"]


async def _cashfree_payment(env, request_id, transfer_text_id, reference):
    await env.sql(
        """insert into salon_payout_payments(payout_id, reference, method, paid_at, amount_paid_paise, source,
                                              transfer_id)
           values(:p, :ref, 'imps', now(), :a, 'transfer', :t)""",
        p=request_id, ref=reference, a=AMOUNT, t=transfer_text_id)


async def _transfer_text_id(env, row_id):
    return (await env.sql("select transfer_id from salon_payout_transfers where id = :i", i=row_id))[0]["transfer_id"]


async def test_only_one_live_transfer_per_request_but_a_failed_one_can_be_retried(env):
    f = await env.seed()
    request = await _request(env, f)
    first = await _transfer(env, request)

    with pytest.raises(IntegrityError):
        await _transfer(env, request, attempt=2)

    await env.sql("update salon_payout_transfers set status = 'failed', provider_status = 'FAILED' where id = :i", i=first)
    second = await _transfer(env, request, attempt=2)
    assert await _status(env, "salon_payout_transfers", second) == "pending"


async def test_a_transfer_needs_a_waiting_request_and_its_exact_amount(env):
    f = await env.seed()
    request = await _request(env, f)
    with pytest.raises(DBAPIError, match="payout_transfer_amount_must_match_request"):
        await _transfer(env, request, amount=AMOUNT - 1)

    await env.sql(
        "update salon_payout_requests set status = 'cancelled', cancelled_at = now() where id = :r", r=request
    )
    with pytest.raises(DBAPIError, match="payout_transfer_needs_waiting_request"):
        await _transfer(env, request)


async def test_cancel_and_reject_are_refused_while_a_transfer_is_pending_or_successful(env):
    f = await env.seed()
    request = await _request(env, f)
    transfer = await _transfer(env, request)

    for statement in (
        "update salon_payout_requests set status = 'cancelled', cancelled_at = now() where id = :r",
        "update salon_payout_requests set status = 'rejected', reject_reason = 'no', processed_at = now() where id = :r",
    ):
        with pytest.raises(DBAPIError, match="payout_transfer_in_progress"):
            await env.sql(statement, r=request)

    await env.sql("update salon_payout_transfers set status = 'success', utr = 'UTR1' where id = :i", i=transfer)
    with pytest.raises(DBAPIError, match="payout_transfer_in_progress"):
        await env.sql("update salon_payout_requests set status = 'cancelled', cancelled_at = now() where id = :r", r=request)


async def test_a_failed_transfer_leaves_the_request_free_to_reject_or_cancel(env):
    f = await env.seed()
    request = await _request(env, f)
    transfer = await _transfer(env, request)
    await env.sql("update salon_payout_transfers set status = 'failed', failure_reason = 'bank said no' where id = :i", i=transfer)

    await env.sql(
        "update salon_payout_requests set status = 'rejected', reject_reason = 'declined', processed_at = now() where id = :r",
        r=request,
    )
    assert await _status(env, "salon_payout_requests", request) == "rejected"


async def test_a_successful_transfer_pays_the_request_without_a_proof_file(env):
    f = await env.seed()
    request = await _request(env, f)
    transfer = await _transfer(env, request)
    transfer_text = await _transfer_text_id(env, transfer)
    await env.sql("update salon_payout_transfers set status = 'success', utr = 'UTR-OK' where id = :i", i=transfer)
    await _cashfree_payment(env, request, transfer_text, "UTR-OK")

    await env.sql(
        "update salon_payout_requests set status = 'paid', reference = 'UTR-OK', processed_at = now() where id = :r",
        r=request,
    )
    assert await _status(env, "salon_payout_requests", request) == "paid"


async def test_a_provider_payment_counts_only_after_its_transfer_succeeded(env):
    f = await env.seed()
    request = await _request(env, f)
    transfer = await _transfer(env, request)
    await _cashfree_payment(env, request, await _transfer_text_id(env, transfer), "UTR-EARLY")

    with pytest.raises(DBAPIError, match="payout_transfer_not_successful"):
        await env.sql(
            "update salon_payout_requests set status = 'paid', reference = 'UTR-EARLY', processed_at = now() where id = :r",
            r=request,
        )


async def test_a_by_hand_payment_is_refused_while_a_transfer_is_live(env):
    f = await env.seed()
    request = await _request(env, f)
    await _transfer(env, request)
    proof = (await env.sql(
        """insert into payout_proofs(mime_type, size_bytes, sha256, content)
           values('application/pdf', 3, repeat('b', 64), '\\x010203'::bytea) returning id"""))[0]["id"]
    await env.sql(
        """insert into salon_payout_payments(payout_id, reference, method, paid_at, amount_paid_paise, proof_id)
           values(:p, 'MANUAL-1', 'upi', now(), :a, :proof)""", p=request, a=AMOUNT, proof=proof)

    with pytest.raises(DBAPIError, match="payout_transfer_in_progress"):
        await env.sql(
            "update salon_payout_requests set status = 'paid', reference = 'MANUAL-1', processed_at = now() where id = :r",
            r=request,
        )


async def test_a_manual_payment_still_needs_its_proof_and_a_provider_one_needs_its_transfer_id(env):
    f = await env.seed()
    request = await _request(env, f)
    with pytest.raises(IntegrityError):
        await env.sql(
            """insert into salon_payout_payments(payout_id, reference, method, paid_at, amount_paid_paise)
               values(:p, 'NO-PROOF', 'upi', now(), :a)""", p=request, a=AMOUNT)
    with pytest.raises(IntegrityError):
        await env.sql(
            """insert into salon_payout_payments(payout_id, reference, method, paid_at, amount_paid_paise, source)
               values(:p, 'NO-TRANSFER', 'imps', now(), :a, 'transfer')""", p=request, a=AMOUNT)


async def test_transfer_fields_are_frozen_and_the_status_only_moves_forward(env):
    f = await env.seed()
    request = await _request(env, f)
    transfer = await _transfer(env, request)

    with pytest.raises(DBAPIError, match="payout_transfer_fields_are_frozen"):
        await env.sql("update salon_payout_transfers set amount_paise = 1 where id = :i", i=transfer)
    with pytest.raises(DBAPIError, match="payout_records_are_never_deleted"):
        await env.sql("delete from salon_payout_transfers where id = :i", i=transfer)

    await env.sql("update salon_payout_transfers set status = 'failed' where id = :i", i=transfer)
    with pytest.raises(DBAPIError, match="payout_transfer_status_is_final"):
        await env.sql("update salon_payout_transfers set status = 'reversed' where id = :i", i=transfer)
    # The provider is the source of truth: a failure it later reports as a success is real money.
    await env.sql("update salon_payout_transfers set status = 'success', utr = 'LATE' where id = :i", i=transfer)
    assert await _status(env, "salon_payout_transfers", transfer) == "success"


async def test_a_success_can_be_reversed_by_the_bank_and_nothing_else_moves_it(env):
    f = await env.seed()
    request = await _request(env, f)
    transfer = await _transfer(env, request)
    await env.sql("update salon_payout_transfers set status = 'success', utr = 'U' where id = :i", i=transfer)
    await env.sql("update salon_payout_transfers set status = 'reversed' where id = :i", i=transfer)
    assert await _status(env, "salon_payout_transfers", transfer) == "reversed"
    with pytest.raises(DBAPIError, match="payout_transfer_status_is_final"):
        await env.sql("update salon_payout_transfers set status = 'success' where id = :i", i=transfer)


async def test_provider_events_are_audited_without_an_admin(env):
    f = await env.seed()
    request = await _request(env, f)
    for action in ("send_transfer", "transfer_success", "transfer_failed", "transfer_reversed", "transfer_conflict"):
        await env.sql("insert into payout_audit(payout_id, action) values(:p, :a)", p=request, a=action)
    with pytest.raises(IntegrityError):
        await env.sql("insert into payout_audit(payout_id, action) values(:p, 'made_up')", p=request)


async def test_erasing_a_salon_removes_its_transfers_too(env):
    f = await env.seed()
    request = await _request(env, f)
    transfer = await _transfer(env, request)
    await env.sql("update salon_payout_transfers set status = 'success', utr = 'U-ERASE' where id = :i", i=transfer)
    await _cashfree_payment(env, request, await _transfer_text_id(env, transfer), "U-ERASE")
    await env.sql(
        "update salon_payout_requests set status = 'paid', reference = 'U-ERASE', processed_at = now() where id = :r",
        r=request,
    )

    await env.sql("select erase_salon(:s)", s=f["salon"])

    assert await support.count(env, "salon_payout_transfers", "request_id = :r", r=request) == 0
    assert await support.count(env, "salon_payout_requests", "salon_id = :s", s=f["salon"]) == 0


# ------------------------------------------------------------------------------------------
# The real use case and repository on PostgreSQL, with only the provider faked.
# ------------------------------------------------------------------------------------------
from app.application.ports.payout_transfer import (
    PayoutTransferGateway,
    TransferResult,
)
from app.application.use_cases.payout_proof import PayoutProofUseCases
from app.application.use_cases.payout_transfer import PayoutTransferUseCases
from app.application.use_cases.wallet import WalletAdminUseCases, WalletUseCases
from app.core.exceptions import PayoutTransferInProgressError
from app.domain.entities.profile import Role
from app.infrastructure.db.repositories.payout_proof_repository import (
    PayoutProofRepository,
)
from tests.conftest import make_profile, make_super_admin


class ScriptedProvider(PayoutTransferGateway):
    provider_name = "fake"

    def __init__(self, status="RECEIVED", utr=None):
        self.status, self.utr = status, utr
        self.sent = []
        self.final = {}  # a transfer that ended keeps its own answer, whatever the next attempt does

    async def upsert_beneficiary(self, beneficiary):
        self.beneficiary = beneficiary

    async def create_transfer(self, request):
        self.sent.append(request)
        if self.status in ("FAILED", "SUCCESS"):
            self.final[request.transfer_id] = (self.status, self.utr)
        return TransferResult(transfer_id=request.transfer_id, status=self.status, utr=self.utr, cf_transfer_id="77")

    async def get_transfer(self, transfer_id):
        status, utr = self.final.get(transfer_id, (self.status, self.utr))
        return TransferResult(transfer_id=transfer_id, status=status, utr=utr)

    def verify_webhook_signature(self, raw_body, headers):
        return True

    def parse_webhook(self, raw_body):
        return None


class Notices:
    def __init__(self):
        self.paid_calls = []

    async def paid(self, *args):
        self.paid_calls.append(args)


async def _admin(env):
    """A real super admin profile (transfers and audit rows reference profiles)."""

    admin_id = str(uuid4())
    await env.sql("insert into auth.users(id, email) values(:i, :e)", i=admin_id, e=admin_id + "@example.test")
    # The new-user trigger creates the profile; promote it.
    await env.sql("update profiles set role = cast('super_admin' as user_role) where id = :i", i=admin_id)
    return make_super_admin(id=admin_id)


async def _ready_request(env, *, phone="9876543210", upi=None):
    """A salon with a saved bank account, an owner phone, and a waiting request."""

    f = await env.seed()
    await env.sql("update profiles set phone = :p, full_name = 'Asha Rao' where id = :o", p=phone, o=f["owner"])
    await env.sql(
        """insert into salon_payout_accounts (salon_id, account_holder_name, upi_id, bank_name,
                                               bank_account_number, ifsc)
           values (:s, 'Asha Rao', :u, 'HDFC', '123456789012', 'HDFC0000001')""", s=f["salon"], u=upi)
    return f, await _request(env, f)


async def test_sending_through_the_provider_then_success_pays_the_request_and_lowers_the_balance(env):
    _, request = await _ready_request(env)
    provider, notices = ScriptedProvider(status="RECEIVED"), Notices()
    admin = await _admin(env)
    async with env.session() as session:
        repository = PayoutProofRepository(session)
        uc = PayoutTransferUseCases(repository, provider, notices=notices)
        await uc.send(admin, str(request))
        detail = await PayoutProofUseCases(repository).detail(admin, str(request))
        assert detail["status"] == "requested" and detail["processing"] is True
        assert detail["transfer"]["status"] == "pending" and detail["transfer"]["mode"] == "imps"
        assert provider.beneficiary.phone == "9876543210" and provider.beneficiary.name == "Asha Rao"

        provider.status, provider.utr = "SUCCESS", "UTRSANDBOX01"
        await uc.refresh(admin, str(request))
        paid = await PayoutProofUseCases(repository).detail(admin, str(request))

    assert paid["status"] == "paid" and paid["reference"] == "UTRSANDBOX01" and paid["processing"] is False
    assert paid["payment"]["source"] == "transfer" and paid["payment"]["proof_mime"] is None
    assert paid["transfer"]["status"] == "success" and paid["transfer"]["utr"] == "UTRSANDBOX01"
    assert [t["action"] for t in paid["timeline"]] == ["send_transfer", "transfer_success"]
    assert notices.paid_calls and notices.paid_calls[0][3] == "UTRSANDBOX01"
    assert (await env.sql("select status from salon_payout_requests where id = :r", r=request))[0]["status"] == "paid"


async def test_while_the_transfer_is_pending_the_owner_cannot_cancel_and_the_admin_cannot_decline_or_pay_by_hand(env):
    f, request = await _ready_request(env)
    admin, owner = await _admin(env), make_profile(id=f["owner"], role=Role.owner)
    async with env.session() as session:
        repository = PayoutProofRepository(session)
        await PayoutTransferUseCases(repository, ScriptedProvider("RECEIVED")).send(admin, str(request))

        feed = await repository.entries(f["salon"], None, 10)
        payout = next(row for row in feed[0] if row["kind"] == "payout")
        assert payout["processing"] is True and payout["can_cancel"] is False

        wallet = WalletUseCases(repository, online_payments_live=True)
        with pytest.raises(PayoutTransferInProgressError):
            await wallet.cancel_payout(owner, str(request))
        with pytest.raises(PayoutTransferInProgressError):
            await WalletAdminUseCases(repository).reject(admin, str(request), "not today")
        with pytest.raises(PayoutTransferInProgressError):
            await PayoutProofUseCases(repository).pay(
                admin, str(request), reference="MANUAL-1", method="upi", paid_at=datetime.now(UTC),
                amount_paid_paise=AMOUNT, adjustment_reason=None, note=None, proof=b"\x89PNG\r\n\x1a\n" + b"0" * 64)

    assert (await env.sql("select status from salon_payout_requests where id = :r", r=request))[0]["status"] == "requested"


async def test_a_failed_transfer_frees_the_request_and_the_admin_can_send_again(env):
    _, request = await _ready_request(env, upi="asha@okhdfc")
    admin = await _admin(env)
    provider = ScriptedProvider("FAILED")
    async with env.session() as session:
        repository = PayoutProofRepository(session)
        uc = PayoutTransferUseCases(repository, provider)
        await uc.send(admin, str(request))
        assert (await PayoutProofUseCases(repository).detail(admin, str(request)))["transfer"]["status"] == "failed"

        provider.status = "RECEIVED"
        await uc.send(admin, str(request))
        transfers = await repository.transfers(str(request))

    assert [t["status"] for t in transfers] == ["failed", "pending"]
    assert [t["mode"] for t in transfers] == ["upi", "upi"]  # a saved UPI id wins for a small amount
    assert transfers[0]["transfer_id"].endswith("_1") and transfers[1]["transfer_id"].endswith("_2")


async def test_the_admin_queue_marks_a_request_with_a_live_transfer_as_processing(env):
    _, request = await _ready_request(env)
    admin = await _admin(env)
    async with env.session() as session:
        repository = PayoutProofRepository(session)
        before, _ = await repository.queue("requested", None, 50)
        await PayoutTransferUseCases(repository, ScriptedProvider("RECEIVED")).send(admin, str(request))
        after, _ = await repository.queue("requested", None, 50)

    assert next(r for r in before if r["id"] == str(request))["processing"] is False
    assert next(r for r in after if r["id"] == str(request))["processing"] is True


# ------------------------------------------------------------------------------------------
# Two real connections: the database alone must hold when the app's own locks are not in play.
# ------------------------------------------------------------------------------------------
import asyncio

from sqlalchemy import text

_INSERT = text(
    """insert into salon_payout_transfers(request_id, transfer_id, beneficiary_id, mode, amount_paise)
       values (cast(:r as uuid), :t, 'bene_1', 'imps', :a)"""
)
_CANCEL = text("update salon_payout_requests set status = 'cancelled', cancelled_at = now() where id = cast(:r as uuid)")


async def test_a_transfer_started_while_a_cancel_is_uncommitted_waits_and_is_then_refused(env):
    f = await env.seed()
    request = await _request(env, f)
    async with env.session() as cancelling, env.session() as starting:
        await cancelling.execute(_CANCEL, {"r": str(request)})
        insert = asyncio.create_task(starting.execute(_INSERT, {"r": str(request), "t": "po_race_1", "a": AMOUNT}))
        await asyncio.sleep(0.6)
        assert not insert.done()  # waiting for the cancel, not racing past it
        await cancelling.commit()
        with pytest.raises(DBAPIError, match="payout_transfer_needs_waiting_request"):
            await insert
    assert await support.count(env, "salon_payout_transfers", "request_id = :r", r=request) == 0


async def test_a_cancel_started_while_a_transfer_is_uncommitted_waits_and_is_then_refused(env):
    f = await env.seed()
    request = await _request(env, f)
    async with env.session() as starting, env.session() as cancelling:
        await starting.execute(_INSERT, {"r": str(request), "t": "po_race_2", "a": AMOUNT})
        cancel = asyncio.create_task(cancelling.execute(_CANCEL, {"r": str(request)}))
        await asyncio.sleep(0.6)
        assert not cancel.done()
        await starting.commit()
        with pytest.raises(DBAPIError, match="payout_transfer_in_progress"):
            await cancel
    assert (await env.sql("select status from salon_payout_requests where id = :r", r=request))[0]["status"] == "requested"
