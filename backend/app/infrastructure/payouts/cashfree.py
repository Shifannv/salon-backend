"""Cashfree Payouts (V2) adapter: send a salon's payout to its bank or UPI account.

A separate Cashfree product from the Payment Gateway, with its own keys (``CASHFREE_PAYOUT_*``).
Deleting this file removes automatic payout; the super admin can still pay by hand.

Evidence level: BUILT and TESTED LOCALLY through ``httpx.MockTransport``; the sandbox run is the
acceptance step. Request shapes follow Cashfree's Payouts V2 reference (``x-api-version``
2024-01-01): ``POST /payout/beneficiary``, ``POST /payout/transfers``,
``GET /payout/transfers?transfer_id=``.

Safety rules:
* A transfer is identified by OUR ``transfer_id`` (request + attempt). A timeout or 5xx raises
  ``PayoutOutcomeUnknownError``: the caller looks the transfer up, never sends it again.
* A beneficiary that already exists is success (its id is content-addressed from the account).
* The full account number and the client secret are never logged.
* Webhook signature = Base64(HMAC-SHA256(key=client secret, msg=timestamp + raw body)).
"""

import base64
import hashlib
import hmac
import json
import logging
import re
import time
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import httpx

from app.application.ports.payout_transfer import (
    BeneficiaryRequest,
    PayoutTransferGateway,
    TransferRequest,
    TransferResult,
)
from app.core.config import Settings
from app.core.exceptions import PayoutOutcomeUnknownError, PayoutProviderError
from app.core.telemetry import measure_external
from app.domain.services.payout_transfer import rupees
from app.infrastructure.webhook_signing import header

logger = logging.getLogger(__name__)

PROVIDER = "cashfree"

_BASE_URL = {
    "sandbox": "https://sandbox.cashfree.com/payout",
    "production": "https://api.cashfree.com/payout",
}

_TRANSFER_EVENTS = {
    "TRANSFER_SUCCESS", "TRANSFER_ACKNOWLEDGED", "TRANSFER_FAILED", "TRANSFER_REVERSED", "TRANSFER_REJECTED",
}
_AMOUNT_TOKEN = "@@amount@@"


def _dumps(body: Mapping[str, Any], amount: Decimal | None = None) -> bytes:
    """JSON with the rupee amount as an exact number (no float round trip)."""

    text = json.dumps(body, separators=(",", ":"))
    if amount is not None:
        text = text.replace(f'"{_AMOUNT_TOKEN}"', f"{amount:.2f}")
    return text.encode()


def _result(document: Mapping[str, Any]) -> TransferResult:
    data = document.get("data") if isinstance(document.get("data"), Mapping) else document
    cf_id = data.get("cf_transfer_id")
    description = data.get("status_description")
    return TransferResult(
        transfer_id=str(data.get("transfer_id", "")),
        status=str(data.get("status") or "").upper(),
        cf_transfer_id=str(cf_id) if cf_id is not None else None,
        status_code=(str(data["status_code"]) if data.get("status_code") else None),
        utr=str(data.get("transfer_utr") or data.get("utr") or "") or None,
        description=str(description)[:200] if description else None,
    )


def create_gateway(settings: Settings) -> PayoutTransferGateway:
    """Entry point the resolver calls by module name (``PAYOUT_PROVIDER=cashfree``)."""

    return CashfreePayoutGateway(settings)


class CashfreePayoutGateway(PayoutTransferGateway):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._client_id = settings.cashfree_payout_client_id or ""
        self._secret = (
            settings.cashfree_payout_client_secret.get_secret_value()
            if settings.cashfree_payout_client_secret
            else ""
        )
        self._base_url = _BASE_URL[settings.cashfree_payout_environment]
        self._api_version = settings.cashfree_payout_api_version
        self._timeout = settings.payment_provider_timeout_seconds
        self._tolerance = settings.cashfree_webhook_tolerance_seconds
        self._client = client

    @property
    def provider_name(self) -> str:
        return PROVIDER

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=5.0))
        return self._client

    @measure_external("cashfree_payouts")
    async def _request(
        self, method: str, path: str, *, body: bytes | None = None, accept: tuple[int, ...] = ()
    ) -> tuple[int, Any]:
        """The status and parsed body. Statuses in ``accept`` are returned, not raised."""

        headers = {
            "x-client-id": self._client_id,
            "x-client-secret": self._secret,
            "x-api-version": self._api_version,
            "accept": "application/json",
        }
        if body is not None:
            headers["content-type"] = "application/json"
        try:
            response = await self._http().request(method, f"{self._base_url}{path}", content=body, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("Payout provider unreachable: %s %s", method, path.split("?")[0])
            raise PayoutOutcomeUnknownError("The payout provider is unreachable") from exc
        document: Any = None
        try:
            document = json.loads(response.content) if response.content else None
        except ValueError:
            document = None
        if response.status_code in accept or response.status_code < 400:
            return response.status_code, document
        code = document.get("code") if isinstance(document, Mapping) else None
        logger.warning(
            "Payout provider answered %s %s: status=%s code=%s",
            method, path.split("?")[0], response.status_code, code,
        )
        # 5xx, timeouts and rate limits: the request may have been processed. Anything else is a refusal.
        unknown = response.status_code >= 500 or response.status_code in (408, 429)
        error_class = PayoutOutcomeUnknownError if unknown else PayoutProviderError
        raise error_class(
            "The payout provider did not accept the request",
            {"provider_status": response.status_code, "provider_code": str(code)[:60] if code else None},
        )

    # ------------------------------------------------------------------ beneficiary
    async def upsert_beneficiary(self, beneficiary: BeneficiaryRequest) -> None:
        if beneficiary.mode == "upi":
            instrument: dict[str, Any] = {"vpa": beneficiary.vpa}
        else:
            instrument = {"bank_account_number": beneficiary.bank_account_number, "bank_ifsc": beneficiary.ifsc}
        body = {
            "beneficiary_id": beneficiary.beneficiary_id,
            "beneficiary_name": beneficiary.name,
            "beneficiary_instrument_details": instrument,
            "beneficiary_contact_details": {"beneficiary_phone": beneficiary.phone},
        }
        # 409: this beneficiary already exists (its id is built from the account, so it is the same account).
        await self._request("POST", "/beneficiary", body=_dumps(body), accept=(409,))

    # ---------------------------------------------------------------------- transfer
    async def create_transfer(self, request: TransferRequest) -> TransferResult:
        body = {
            "transfer_id": request.transfer_id,
            "transfer_amount": _AMOUNT_TOKEN,
            "transfer_currency": "INR",
            "transfer_mode": request.mode,
            "beneficiary_details": {"beneficiary_id": request.beneficiary_id},
            "transfer_remarks": request.remarks[:70],
        }
        status, document = await self._request(
            "POST", "/transfers", body=_dumps(body, rupees(request.amount_paise)), accept=(409,)
        )
        if status == 409:
            # Our transfer id is already known to the provider: it was created, so read it back.
            existing = await self.get_transfer(request.transfer_id)
            if existing is None:
                # The provider proved it knows this id but will not show it: still unknown, never a failure.
                raise PayoutOutcomeUnknownError("The payout provider reported a conflict for this transfer")
            return existing
        if not isinstance(document, Mapping):
            raise PayoutOutcomeUnknownError("The payout provider returned an unreadable answer")
        result = _result(document)
        return result if result.transfer_id else _result({**document, "transfer_id": request.transfer_id})

    async def get_transfer(self, transfer_id: str) -> TransferResult | None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", transfer_id):
            raise ValueError("transfer_id is not a valid payout transfer id")
        status, document = await self._request("GET", f"/transfers?transfer_id={transfer_id}", accept=(404,))
        if status == 404 or not isinstance(document, Mapping):
            return None
        return _result(document)

    # ---------------------------------------------------------------------- webhooks
    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        signature = header(headers, "x-webhook-signature")
        timestamp = header(headers, "x-webhook-timestamp")
        if not signature or not timestamp or not self._secret:
            return False
        try:
            stamp = int(timestamp)
        except ValueError:
            return False
        seconds = stamp / 1000 if stamp > 10**11 else stamp
        if abs(time.time() - seconds) > self._tolerance:
            return False
        digest = hmac.new(self._secret.encode(), timestamp.encode() + raw_body, hashlib.sha256).digest()
        return hmac.compare_digest(base64.b64encode(digest), signature.encode("utf-8", "ignore"))

    def parse_webhook(self, raw_body: bytes) -> TransferResult | None:
        try:
            document = json.loads(raw_body)
            event = str(document["type"])
        except (ValueError, KeyError, TypeError):
            return None
        if event == "LOW_BALANCE_ALERT":
            logger.warning("Cashfree Payouts balance is low: top it up or automatic payouts will fail")
            return None
        if event not in _TRANSFER_EVENTS or not isinstance(document.get("data"), Mapping):
            return None
        result = _result(document)
        return result if result.transfer_id else None
