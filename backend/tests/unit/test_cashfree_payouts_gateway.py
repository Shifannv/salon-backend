"""Cashfree Payouts adapter and the pure payout transfer rules. No network: httpx.MockTransport only.

Evidence level: tested locally. Nothing here proves behaviour against the real provider; the sandbox
run is the acceptance step.
"""

import base64
import hashlib
import hmac
import json
import logging
import time

import httpx
import pytest
from pydantic import ValidationError as PydanticValidationError

from app.application.ports.payout_transfer import BeneficiaryRequest, TransferRequest
from app.core.config import Settings
from app.core.exceptions import (
    PaymentProviderNotConfiguredError,
    PayoutOutcomeUnknownError,
    PayoutProviderError,
)
from app.domain.services.payout_transfer import (
    IMPS_LIMIT_PAISE,
    UPI_LIMIT_PAISE,
    TransferProblem,
    beneficiary_id_for,
    choose_mode,
    clean_beneficiary_name,
    map_status,
    normalize_phone,
    transfer_id_for,
)
from app.infrastructure.payouts import cashfree as cp
from app.infrastructure.payouts.resolver import build_payout_gateway

SECRET = "payout_secret_for_tests"
ACCOUNT_NUMBER = "123456789012"
REQUEST = "0b3f2c1a-7d4e-4a55-9f60-1c2d3e4f5a6b"


def payout_settings(**kw) -> Settings:
    values = {
        "_env_file": None, "environment": "test", "payout_provider": "cashfree",
        "cashfree_payout_client_id": "pid", "cashfree_payout_client_secret": SECRET,
    }
    values.update(kw)
    return Settings(**values)


def gateway(handler, **kw) -> cp.CashfreePayoutGateway:
    return cp.CashfreePayoutGateway(
        payout_settings(**kw), httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def transfer(**kw) -> TransferRequest:
    values = {
        "transfer_id": transfer_id_for(REQUEST, 1), "beneficiary_id": "sl_abc_123", "amount_paise": 25_050,
        "mode": "imps", "remarks": "Salon payout 0b3f2c1a",
    }
    values.update(kw)
    return TransferRequest(**values)


def signed(body: bytes, *, secret: str = SECRET, stamp: int | None = None) -> dict[str, str]:
    timestamp = str(stamp if stamp is not None else int(time.time()))
    digest = hmac.new(secret.encode(), timestamp.encode() + body, hashlib.sha256).digest()
    return {"x-webhook-timestamp": timestamp, "x-webhook-signature": base64.b64encode(digest).decode()}


# ------------------------------------------------------------------ rules
class TestRules:
    def test_upi_is_used_when_saved_and_the_amount_fits(self):
        assert choose_mode(50_000, has_upi=True, has_bank=True) == "upi"

    def test_a_large_amount_goes_to_the_bank_by_imps(self):
        assert choose_mode(UPI_LIMIT_PAISE + 1, has_upi=True, has_bank=True) == "imps"
        assert choose_mode(50_000, has_upi=False, has_bank=True) == "imps"

    def test_no_account_or_too_large_an_amount_is_refused_with_a_safe_message(self):
        with pytest.raises(TransferProblem, match="not saved"):
            choose_mode(50_000, has_upi=False, has_bank=False)
        with pytest.raises(TransferProblem, match="above"):
            choose_mode(IMPS_LIMIT_PAISE + 1, has_upi=False, has_bank=True)
        with pytest.raises(TransferProblem, match="above"):
            choose_mode(UPI_LIMIT_PAISE + 1, has_upi=True, has_bank=False)

    def test_ids_fit_the_provider_limits_and_change_only_with_the_attempt_or_account(self):
        assert len(transfer_id_for(REQUEST, 1)) <= 40 and transfer_id_for(REQUEST, 1) != transfer_id_for(REQUEST, 2)
        a = beneficiary_id_for(REQUEST, "123|HDFC0000001")
        assert a == beneficiary_id_for(REQUEST, "123|HDFC0000001")
        assert a != beneficiary_id_for(REQUEST, "124|HDFC0000001")
        assert len(a) <= 50

    def test_status_mapping_never_calls_an_unknown_status_a_success(self):
        assert map_status("SUCCESS") == "success"
        assert {map_status(s) for s in ("FAILED", "REJECTED", "MANUALLY_REJECTED")} == {"failed"}
        assert map_status("REVERSED") == "reversed"
        assert {map_status(s) for s in ("RECEIVED", "PENDING", "QUEUED", "APPROVAL_PENDING", "", None, "WHAT")} == {"pending"}

    def test_the_beneficiary_id_is_keyed_so_an_account_number_cannot_be_guessed_from_it(self):
        plain = beneficiary_id_for(REQUEST, "123456789012|HDFC0000001")
        keyed = beneficiary_id_for(REQUEST, "123456789012|HDFC0000001", "server-secret")
        assert keyed != plain and keyed != beneficiary_id_for(REQUEST, "123456789012|HDFC0000001", "other-secret")
        assert keyed != beneficiary_id_for("another-salon", "123456789012|HDFC0000001", "server-secret")
        assert keyed == beneficiary_id_for(REQUEST, "123456789012|HDFC0000001", "server-secret")
        assert len(keyed) <= 50 and "123456789012" not in keyed

    def test_names_and_phones_are_made_acceptable(self):
        assert clean_beneficiary_name("Asha  R. <script>") == "Asha R. script"
        assert clean_beneficiary_name("???") == "Salon Owner"
        assert normalize_phone("+91 98765-43210") == "9876543210"
        assert normalize_phone("12345") is None


# ---------------------------------------------------------------- resolver
class TestResolver:
    def test_none_means_no_automatic_payout(self):
        assert build_payout_gateway(Settings(_env_file=None, environment="test")) is None

    def test_cashfree_is_loaded_by_name_and_is_named_for_the_webhook_path(self):
        gateway = build_payout_gateway(payout_settings())
        assert isinstance(gateway, cp.CashfreePayoutGateway) and gateway.provider_name == "cashfree"

    def test_an_unknown_or_malformed_provider_name_is_refused(self):
        with pytest.raises(PaymentProviderNotConfiguredError):
            build_payout_gateway(payout_settings(payout_provider="nope"))
        with pytest.raises(PaymentProviderNotConfiguredError):
            build_payout_gateway(payout_settings(payout_provider="../x"))


# ---------------------------------------------------------------- config
class TestConfig:
    def test_enabling_payouts_needs_both_keys(self):
        with pytest.raises(PydanticValidationError, match="CASHFREE_PAYOUT_CLIENT_SECRET"):
            payout_settings(cashfree_payout_client_secret=None)

    def test_production_payouts_need_the_live_acknowledgement(self):
        with pytest.raises(PydanticValidationError, match="PAYMENT_ALLOW_LIVE"):
            payout_settings(cashfree_payout_environment="production", payment_allow_live=False)

    @pytest.mark.parametrize("environment", ["staging", "production"])
    def test_outside_local_and_test_payouts_need_mfa_and_the_encryption_key(self, environment):
        with pytest.raises(PydanticValidationError, match="ADMIN_REQUIRE_MFA"):
            payout_settings(environment=environment, admin_require_mfa=False, payout_encryption_key="k" * 44)
        with pytest.raises(PydanticValidationError, match="PAYOUT_ENCRYPTION_KEY"):
            payout_settings(environment=environment, admin_require_mfa=True)

    def test_local_and_test_need_neither_so_development_stays_easy(self):
        assert payout_settings(environment="local", admin_require_mfa=False).payout_provider == "cashfree"

    def test_payouts_are_off_by_default(self):
        assert Settings(_env_file=None, environment="test").payout_provider == "none"


# --------------------------------------------------------------- transfers
class TestTransfers:
    async def test_the_transfer_body_headers_and_exact_rupee_amount(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"], seen["headers"], seen["body"] = str(request.url), request.headers, request.content
            return httpx.Response(200, json={"transfer_id": "x", "cf_transfer_id": 77, "status": "RECEIVED"})

        result = await gateway(handler).create_transfer(transfer())

        assert seen["url"] == "https://sandbox.cashfree.com/payout/transfers"
        assert seen["headers"]["x-client-id"] == "pid" and seen["headers"]["x-client-secret"] == SECRET
        assert seen["headers"]["x-api-version"] == "2024-01-01"
        assert b'"transfer_amount":250.50' in seen["body"]  # a JSON number, exact to the paisa
        body = json.loads(seen["body"])
        assert body["transfer_mode"] == "imps" and body["transfer_currency"] == "INR"
        assert body["beneficiary_details"] == {"beneficiary_id": "sl_abc_123"}
        assert result.status == "RECEIVED" and result.cf_transfer_id == "77"
        assert result.transfer_id == "x"

    async def test_production_uses_the_production_host(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            return httpx.Response(200, json={"transfer_id": "x", "status": "SUCCESS"})

        g = gateway(handler, cashfree_payout_environment="production", payment_allow_live=True)
        await g.create_transfer(transfer())
        assert seen["url"].startswith("https://api.cashfree.com/payout/")

    @pytest.mark.parametrize("status_code", [500, 502, 503, 408, 429])
    async def test_a_server_error_or_rate_limit_is_an_unknown_outcome_never_a_failure(self, status_code):
        g = gateway(lambda r: httpx.Response(status_code, json={"code": "boom"}))
        with pytest.raises(PayoutOutcomeUnknownError):
            await g.create_transfer(transfer())

    async def test_a_timeout_or_dropped_connection_is_an_unknown_outcome(self):
        def handler(request):
            raise httpx.ReadTimeout("slow")

        with pytest.raises(PayoutOutcomeUnknownError):
            await gateway(handler).create_transfer(transfer())

    async def test_a_validation_refusal_is_a_definite_failure_with_a_safe_code(self):
        g = gateway(lambda r: httpx.Response(422, json={"code": "beneficiary_not_found", "message": "secret text"}))
        with pytest.raises(PayoutProviderError) as caught:
            await g.create_transfer(transfer())
        assert not isinstance(caught.value, PayoutOutcomeUnknownError)
        assert caught.value.details == {"provider_status": 422, "provider_code": "beneficiary_not_found"}
        assert "secret text" not in caught.value.message

    async def test_a_known_transfer_id_is_read_back_not_sent_again(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.method)
            if request.method == "POST":
                return httpx.Response(409, json={"code": "transfer_id_already_exists"})
            assert request.url.params["transfer_id"] == transfer().transfer_id
            return httpx.Response(200, json={"transfer_id": transfer().transfer_id, "status": "SUCCESS",
                                             "transfer_utr": "UTR9"})

        result = await gateway(handler).create_transfer(transfer())
        assert calls == ["POST", "GET"] and result.status == "SUCCESS" and result.utr == "UTR9"

    async def test_a_conflict_the_provider_cannot_show_is_unknown_never_a_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(409, json={"code": "transfer_id_already_exists"})
            return httpx.Response(404, json={"code": "transfer_not_found"})

        with pytest.raises(PayoutOutcomeUnknownError):
            await gateway(handler).create_transfer(transfer())

    async def test_looking_up_a_transfer_the_provider_never_saw_is_none(self):
        g = gateway(lambda r: httpx.Response(404, json={"code": "transfer_not_found"}))
        assert await g.get_transfer(transfer().transfer_id) is None

    async def test_a_malformed_transfer_id_is_refused_before_any_request(self):
        def handler(request):
            raise AssertionError("no request expected")

        with pytest.raises(ValueError):
            await gateway(handler).get_transfer("../etc/passwd")


# ------------------------------------------------------------- beneficiary
class TestBeneficiary:
    async def test_a_bank_account_is_sent_with_its_ifsc_and_an_existing_one_is_success(self, caplog):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return httpx.Response(409, json={"code": "beneficiary_id_already_exists"})

        caplog.set_level(logging.DEBUG)
        await gateway(handler).upsert_beneficiary(BeneficiaryRequest(
            beneficiary_id="sl_1", name="Asha", phone="9876543210", mode="imps",
            bank_account_number=ACCOUNT_NUMBER, ifsc="HDFC0000001",
        ))
        assert seen["body"]["beneficiary_instrument_details"] == {
            "bank_account_number": ACCOUNT_NUMBER, "bank_ifsc": "HDFC0000001"}
        assert seen["body"]["beneficiary_contact_details"] == {"beneficiary_phone": "9876543210"}
        assert ACCOUNT_NUMBER not in caplog.text and SECRET not in caplog.text

    async def test_a_upi_beneficiary_sends_only_the_vpa(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={})

        await gateway(handler).upsert_beneficiary(BeneficiaryRequest(
            beneficiary_id="sl_2", name="Asha", phone="9876543210", mode="upi", vpa="asha@upi"))
        assert seen["body"]["beneficiary_instrument_details"] == {"vpa": "asha@upi"}

    async def test_an_invalid_account_is_a_definite_refusal(self):
        g = gateway(lambda r: httpx.Response(400, json={"code": "bank_ifsc_invalid"}))
        with pytest.raises(PayoutProviderError) as caught:
            await g.upsert_beneficiary(BeneficiaryRequest(
                beneficiary_id="sl_3", name="A", phone="9876543210", mode="imps",
                bank_account_number="1", ifsc="BAD"))
        assert caught.value.details["provider_code"] == "bank_ifsc_invalid"


# ----------------------------------------------------------------- webhooks
class TestWebhooks:
    BODY = json.dumps({
        "type": "TRANSFER_SUCCESS",
        "data": {"transfer_id": "po_1", "cf_transfer_id": "9", "status": "SUCCESS",
                 "status_code": "SENT_TO_BENEFICIARY", "transfer_utr": "UTR1"},
    }).encode()

    def test_a_correctly_signed_fresh_event_is_accepted(self):
        g = gateway(lambda r: httpx.Response(200))
        assert g.verify_webhook_signature(self.BODY, signed(self.BODY)) is True

    def test_a_wrong_secret_a_changed_body_or_missing_headers_are_refused(self):
        g = gateway(lambda r: httpx.Response(200))
        assert g.verify_webhook_signature(self.BODY, signed(self.BODY, secret="other")) is False
        assert g.verify_webhook_signature(self.BODY + b" ", signed(self.BODY)) is False
        assert g.verify_webhook_signature(self.BODY, {}) is False

    def test_a_stale_timestamp_is_refused(self):
        g = gateway(lambda r: httpx.Response(200), cashfree_webhook_tolerance_seconds=60)
        assert g.verify_webhook_signature(self.BODY, signed(self.BODY, stamp=int(time.time()) - 3600)) is False

    def test_a_success_event_is_parsed(self):
        result = gateway(lambda r: httpx.Response(200)).parse_webhook(self.BODY)
        assert (result.transfer_id, result.status, result.utr, result.cf_transfer_id) == ("po_1", "SUCCESS", "UTR1", "9")

    def test_events_the_app_does_not_act_on_are_ignored(self, caplog):
        g = gateway(lambda r: httpx.Response(200))
        assert g.parse_webhook(json.dumps({"type": "BENEFICIARY_INCIDENT", "data": {}}).encode()) is None
        assert g.parse_webhook(b"not json") is None
        assert g.parse_webhook(json.dumps({"type": "TRANSFER_FAILED", "data": {}}).encode()) is None
        with caplog.at_level(logging.WARNING):
            assert g.parse_webhook(json.dumps({"type": "LOW_BALANCE_ALERT", "data": {}}).encode()) is None
        assert "balance is low" in caplog.text
