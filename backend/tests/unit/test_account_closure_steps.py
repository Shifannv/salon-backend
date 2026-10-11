"""Owner closure: cancel -> notify -> refund -> settle -> erase, with in-memory fakes."""

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.ports.auth_admin_gateway import AuthUserContacts
from app.application.ports.payment_gateway import RefundRequest, RefundResult
from app.application.use_cases.account_erasure import (
    AccountErasureService,
    closure_refund_provider_key,
    phone_key_variants,
)
from app.domain.entities.payment import GatewayCapability, RefundStatus
from app.domain.value_objects.money import Money
from app.infrastructure.payments.null import NullPaymentGateway

USER = "11111111-1111-1111-1111-111111111111"
SALON = "22222222-2222-2222-2222-222222222222"
SALON_2 = "22222222-2222-2222-2222-222222222223"
STAFF = "33333333-3333-3333-3333-333333333333"
STAFF_KEPT = "33333333-3333-3333-3333-333333333334"
PAYMENT = "44444444-4444-4444-4444-444444444444"
BOOKING = "55555555-5555-5555-5555-555555555555"


class FakeLedger:
    """The ledger/refund semantics of the SQL adapter, kept in memory."""

    def __init__(self, *, with_payment: bool = True) -> None:
        self.request = {
            "id": "req-1", "user_id": USER, "role": "owner", "salon_id": SALON, "attempts": 0,
            "step_state": {"staff_profile_ids": [STAFF, STAFF_KEPT], "salon_ids": [SALON, SALON_2]},
            "media_keys": [],
        }
        self.status = "pending"
        self.error: str | None = None
        self.delay: int | None = None
        self.events: list[str] = []
        self.present = {USER, STAFF, STAFF_KEPT}  # STAFF_KEPT fails the repository guard
        self.refund: dict | None = None  # the single closure refund row
        self.payment_status = "captured"
        self.with_payment = with_payment
        self.fail_record_step: str | None = None
        self.failed_records: list[tuple[str, str]] = []

    async def claim_due_request(self, stale_seconds):
        if self.status == "completed":
            return None
        self.status = "processing"
        self.request["attempts"] += 1
        return {**self.request, "step_state": dict(self.request["step_state"])}

    async def record_step(self, request_id, step):
        if self.fail_record_step == step:
            self.fail_record_step = None
            raise RuntimeError("crash after the side effect, before recording it")
        self.request["step_state"][step] = True
        self.events.append(f"step:{step}")

    async def fail_request(self, request_id, error_code, delay_seconds):
        self.status, self.error, self.delay = "failed", error_code, delay_seconds

    async def requeue_request(self, request_id, reason_code, delay_seconds):
        self.status, self.error, self.delay = "pending", reason_code, delay_seconds

    async def complete_request(self, request_id):
        self.status = "completed"

    async def cancel_open_bookings(self, user_id):
        self.events.append("cancel+notify")
        return {"cancelled": 2, "notified": 2, "resolved": 1}

    async def list_closure_refund_candidates(self, user_id):
        if not self.with_payment:
            return []
        if self.payment_status not in {"captured", "partially_refunded"} and self.refund is None:
            return []
        return [{
            "payment_id": PAYMENT, "booking_id": BOOKING, "provider": "fakepay",
            "payment_ref": "pay_1", "amount": Decimal("500.00"), "payment_status": self.payment_status,
            "other_refunded": Decimal("0"),
            "refund_id": self.refund["id"] if self.refund else None,
            "refund_status": self.refund["status"] if self.refund else None,
            "refund_ref": self.refund["refund_ref"] if self.refund else None,
        }]

    async def begin_closure_refund(self, payment_id, booking_id, provider, amount):
        if self.refund is None:  # unique (payment_id, idempotency_key)
            self.refund = {"id": "rf-1", "status": "created", "refund_ref": None, "amount": amount}
        return dict(self.refund)

    async def finish_closure_refund(self, refund_id, refund_ref, status, failure_code):
        self.events.append(f"refund:{status}")
        self.refund.update(refund_ref=refund_ref, status=status)
        if status == "processed":
            self.payment_status = "refunded"

    async def record_failed_closure_refund(self, payment_id, booking_id, provider, amount, code):
        self.failed_records.append((payment_id, code))
        self.refund = {"id": "rf-1", "status": "failed", "refund_ref": None, "amount": amount}

    async def list_unsettled_closure_refunds(self, user_id):
        return ["rf-1"] if self.refund and self.refund["status"] == "created" else []

    async def erase_database(self, user_id, role, staff_profile_ids=None):
        self.events.append("erase")
        self.present.discard(user_id)
        self.present.discard(STAFF)

    async def profile_exists(self, user_id):
        return user_id in self.present


class FakeAdmin:
    def __init__(self) -> None:
        self.users = {USER, STAFF, STAFF_KEPT}
        self.banned: list[str] = []
        self.deleted: list[str] = []
        self.phone = "+91 98765 43210"

    async def get_user(self, user_id):
        if user_id not in self.users:
            return None
        return AuthUserContacts(user_id, "a@b.c", True, self.phone, True)

    async def ban_user(self, user_id):
        self.banned.append(user_id)

    async def delete_user(self, user_id):
        self.users.discard(user_id)
        self.deleted.append(user_id)


class FakeGateway(NullPaymentGateway):
    def __init__(self, ledger: FakeLedger, status=RefundStatus.processed, fail=False) -> None:
        self.ledger = ledger
        self.status = status
        self.fail = fail
        self.calls: list[RefundRequest] = []

    @property
    def provider_name(self):
        return "fakepay"

    def supports(self, capability):
        return capability == GatewayCapability.refunds

    async def refund(self, request: RefundRequest) -> RefundResult:
        self.calls.append(request)
        self.ledger.events.append("provider.refund")
        if self.fail:
            raise RuntimeError("provider unreachable")
        return RefundResult("fakepay", "rfnd_1", self.status, request.amount, request.payment_ref)


def build(ledger=None, *, gateway="fake", cap=3, cache_available=True, **kwargs):
    ledger = ledger or FakeLedger()
    admin = FakeAdmin()
    cache = MagicMock()
    cache.available = cache_available
    cache.delete_prefix = AsyncMock()
    refs = MagicMock()
    refs.lock_media_url = AsyncMock()
    refs.media_url_is_referenced = AsyncMock(return_value=False)
    if gateway == "fake":
        gateway = FakeGateway(ledger)
    service = AccountErasureService(
        ledger, admin, MagicMock(), cache, refs, AsyncMock(), "bucket", 600,
        payment_gateway=gateway, refund_max_attempts=cap, cache_required=True, **kwargs)
    return service, ledger, admin, cache, gateway


@pytest.mark.asyncio
async def test_order_is_cancel_notify_refund_settle_then_erase():
    service, ledger, admin, *_ = build()
    await service.process_next()
    assert ledger.status == "completed"
    assert ledger.events == [
        "cancel+notify", "step:bookings_cancelled",
        "provider.refund", "refund:processed", "step:refunds_issued", "step:refunds_settled",
        "step:auth_banned", "erase", "step:db_erased", "step:media_deleted",
        "step:cache_cleared", "step:auth_deleted", "step:staff_auth_deleted",
    ]
    assert admin.banned == [USER, STAFF, STAFF_KEPT]


@pytest.mark.asyncio
async def test_refund_uses_a_deterministic_provider_key_and_the_captured_amount():
    service, _, _, _, gateway = build()
    await service.process_next()
    (call,) = gateway.calls
    assert call.idempotency_key == closure_refund_provider_key(PAYMENT)
    assert call.idempotency_key == closure_refund_provider_key(PAYMENT)  # stable across calls
    assert call.amount == Money(Decimal("500.00")) and call.payment_ref == "pay_1"
    assert call.reason == "salon_closed"


@pytest.mark.asyncio
async def test_refund_is_issued_exactly_once_across_a_retried_run():
    service, ledger, _, _, gateway = build()
    ledger.fail_record_step = "refunds_issued"  # crash AFTER the provider accepted the refund
    await service.process_next()
    assert ledger.status == "failed" and "refunds_issued" not in ledger.request["step_state"]
    assert len(gateway.calls) == 1 and ledger.refund["status"] == "processed"
    await service.process_next()
    assert ledger.status == "completed"
    assert len(gateway.calls) == 1, "the retry must not refund the customer a second time"


@pytest.mark.asyncio
async def test_a_provider_outage_retries_with_the_same_key_and_never_erases_early():
    ledger = FakeLedger()
    service, ledger, _, _, gateway = build(ledger)
    gateway.fail = True
    await service.process_next()
    assert ledger.status == "failed" and ledger.error == "RuntimeError" and ledger.delay >= 30
    assert "erase" not in ledger.events and "auth_banned" not in ledger.request["step_state"]
    gateway.fail = False
    await service.process_next()
    assert ledger.status == "completed"
    assert {c.idempotency_key for c in gateway.calls} == {closure_refund_provider_key(PAYMENT)}


@pytest.mark.asyncio
async def test_unsettled_refund_requeues_with_backoff_and_does_not_fail_the_request():
    service, ledger, admin, _, gateway = build(gateway=None)
    gateway = FakeGateway(ledger, status=RefundStatus.created)
    service.payment_gateway = gateway
    await service.process_next()
    assert ledger.status == "pending" and ledger.error == "refunds_pending" and ledger.delay >= 30
    assert "erase" not in ledger.events and admin.banned == []
    assert ledger.request["step_state"]["refunds_issued"] is True
    assert "refunds_settled" not in ledger.request["step_state"]
    delay_first = ledger.delay
    ledger.refund["status"] = "processed"  # the provider's webhook settled it
    await service.process_next()
    assert ledger.status == "completed" and len(gateway.calls) == 1
    assert delay_first < 3600


@pytest.mark.asyncio
async def test_backoff_grows_while_refunds_stay_unsettled():
    service, ledger, *_ = build(cap=10)
    service.payment_gateway = FakeGateway(ledger, status=RefundStatus.created)
    delays = []
    for _ in range(3):
        await service.process_next()
        delays.append(ledger.delay)
    assert delays == sorted(delays) and delays[0] < delays[-1]


@pytest.mark.asyncio
async def test_after_the_retry_cap_unsettled_refunds_are_logged_and_erasure_proceeds(caplog):
    caplog.set_level(logging.ERROR)
    service, ledger, *_ = build(cap=2)
    service.payment_gateway = FakeGateway(ledger, status=RefundStatus.created)
    await service.process_next()
    assert ledger.status == "pending"
    await service.process_next()  # attempt 2 == cap
    assert ledger.status == "completed"
    assert ledger.refund["status"] == "created"  # left for the operator, not marked failed
    assert any(r.levelno == logging.ERROR and "rf-1" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_a_refund_that_cannot_be_issued_is_recorded_failed_after_the_cap(caplog):
    caplog.set_level(logging.ERROR)
    service, ledger, _, _, gateway = build(cap=2)
    gateway.fail = True
    await service.process_next()
    assert ledger.status == "failed" and ledger.failed_records == []
    await service.process_next()
    assert ledger.status == "completed"
    assert ledger.failed_records == [(PAYMENT, "refund_call_failed")]
    assert any(r.levelno == logging.ERROR for r in caplog.records)


@pytest.mark.asyncio
async def test_a_provider_declining_the_refund_is_recorded_and_does_not_block():
    service, ledger, *_ = build()
    service.payment_gateway = FakeGateway(ledger, status=RefundStatus.failed)
    await service.process_next()
    assert ledger.status == "completed" and ledger.refund["status"] == "failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("gateway", [None, NullPaymentGateway()])
async def test_no_provider_means_no_refund_steps_do_any_work(gateway):
    ledger = FakeLedger(with_payment=False)  # PAYMENT_PROVIDER=none: no online payment can exist
    service, ledger, *_ = build(ledger, gateway=gateway)
    await service.process_next()
    assert ledger.status == "completed"
    assert ledger.refund is None and ledger.failed_records == []
    assert ledger.request["step_state"]["refunds_issued"] and ledger.request["step_state"]["refunds_settled"]


@pytest.mark.asyncio
async def test_an_online_payment_without_a_refund_capable_provider_is_recorded_loudly(caplog):
    caplog.set_level(logging.ERROR)
    service, ledger, *_ = build(gateway=NullPaymentGateway())
    await service.process_next()
    assert ledger.status == "completed"
    assert ledger.failed_records == [(PAYMENT, "provider_unavailable")]
    assert any("cannot be issued" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_customers_skip_the_whole_closure_phase():
    ledger = FakeLedger()
    ledger.request["role"] = "customer"
    ledger.request["step_state"] = {"staff_profile_ids": []}
    service, ledger, *_ = build(ledger)
    await service.process_next()
    assert ledger.status == "completed"
    assert "cancel+notify" not in ledger.events and "provider.refund" not in ledger.events


# ------------------------------------------------------------------- cache clearing
@pytest.mark.asyncio
async def test_cache_clear_covers_every_salon_the_booking_and_walkin_keys_and_the_phone():
    service, _, _, cache, _ = build()
    await service.process_next()
    prefixes = [c.args[0] for c in cache.delete_prefix.await_args_list]
    assert f"salon:{SALON}:" in prefixes and f"salon:{SALON_2}:" in prefixes  # ALL owned salons
    assert f"idempotency:booking:{USER}:" in prefixes
    assert f"idempotency:walkin:v2:{USER}:" in prefixes and f"idempotency:walkin:v2:{STAFF}:" in prefixes
    assert "rate:otp:+919876543210" in prefixes and "rate:otp:919876543210" in prefixes
    assert all(c.kwargs == {"strict": True} for c in cache.delete_prefix.await_args_list)


@pytest.mark.asyncio
async def test_a_cache_failure_is_surfaced_not_swallowed():
    service, ledger, _, cache, _ = build()
    cache.delete_prefix.side_effect = ConnectionError("redis down")
    await service.process_next()
    assert ledger.status == "failed" and ledger.error == "ConnectionError"
    assert "cache_cleared" not in ledger.request["step_state"]
    assert USER in ledger.present or "step:auth_deleted" not in ledger.events  # never "completed"


@pytest.mark.asyncio
async def test_unavailable_cache_blocks_when_redis_is_configured():
    service, ledger, *_ = build(cache_available=False)
    await service.process_next()
    assert ledger.status == "failed" and ledger.error == "ErasureVerificationError"


# ------------------------------------------------------------------ staff identities
@pytest.mark.asyncio
async def test_staff_logins_are_deleted_only_when_their_profile_is_gone():
    service, _, admin, *_ = build()
    await service.process_next()
    assert STAFF in admin.deleted  # profile hard-deleted -> identity removed
    assert STAFF_KEPT not in admin.deleted and STAFF_KEPT in admin.users  # failed the guard: banned only
    assert STAFF_KEPT in admin.banned


def test_phone_key_variants_cover_every_spelling_and_ignore_junk():
    assert phone_key_variants("+91 98765 43210") == ["+91 98765 43210", "+919876543210", "919876543210"]
    assert phone_key_variants(None) == [] and phone_key_variants("12") == []
