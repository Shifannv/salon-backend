"""Ledger helpers: event/observation mapping and the registration details value object."""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.application.ports.payment_gateway import (
    PaymentEvent,
    ProviderPayment,
)
from app.application.use_cases.idempotency import fingerprint_of
from app.domain.entities.payment import (
    LedgerStatus,
    PaymentEventType,
)
from app.infrastructure.db.repositories.payment_repository import PaymentRepository

_log = logging.getLogger("app.application.use_cases.payments")  # keep the pre-split logger name

_EVENT_STATUS = {
    PaymentEventType.payment_authorized: "authorized",
    PaymentEventType.payment_captured: "captured",
    PaymentEventType.payment_failed: "failed",
}
_SETTLED_STATUSES = {
    LedgerStatus.captured,
    LedgerStatus.partially_refunded,
    LedgerStatus.refunded,
}
_SAFE_CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- ")


def _fingerprint(**fields: Any) -> str:
    return fingerprint_of(fields)


def _clean_code(value: str | None) -> str | None:
    """Provider-supplied codes are stored as-is only when they look like codes."""

    if not value:
        return None
    cleaned = "".join(c for c in str(value) if c in _SAFE_CODE_CHARS).strip()[:120]
    return cleaned or None


def _ledger_row(row: dict[str, Any]) -> dict[str, Any]:
    manual = row["channel"] == "manual"
    states = {"captured": "PAID_ONLINE", "created": "PAYMENT_PENDING", "authorized": "PAYMENT_PENDING",
              "refunded": "REFUNDED", "partially_refunded": "PAID_ONLINE", "failed": "FAILED",
              "cancelled": "FAILED", "expired": "FAILED"}
    charge = row.get("online_processing_charge") or Decimal("0")
    return {
        "id": str(row["id"]),
        "booking_id": str(row["booking_id"]),
        "channel": row["channel"],
        "purpose": row["purpose"],
        "settlement_model": row["settlement_model"],
        "provider": row.get("provider"),
        "method": row.get("method"),
        "instrument": row.get("instrument"),
        "amount": row["amount"],
        "currency": row["currency"],
        "status": row["status"],
        "overcollected_amount": row.get("overcollected_amount") or Decimal("0.00"),
        "failure_code": row.get("failure_code"),
        "expires_at": row.get("expires_at"),
        "captured_at": row.get("captured_at"),
        "created_at": row["created_at"],
        "payment_mode": "PAY_AT_SALON" if manual else "PAY_ONLINE",
        "payment_status": "COLLECTED_AT_SALON" if manual else states[row["status"]],
        "collection_method": row.get("collection_method"),
        "service_amount": row.get("service_amount", row["amount"] - charge),
        "online_processing_charge": charge,
        "total_payable": row["amount"],
        "provider_order_reference": row.get("order_ref"),
        "provider_session_id": row.get("provider_session_id"),
        "provider_payment_reference": row.get("payment_ref"),
        "collected_by_owner": row.get("collected_by_owner", False),
        "collected_at": row.get("captured_at") if manual else None,
    }


def event_to_json(event: PaymentEvent) -> dict[str, Any]:
    """Serialise a normalised event for the intake table (identifiers and amounts only)."""

    return {
        "domain": event.domain.value,
        "event_type": event.event_type.value,
        "raw_type": _clean_code(event.raw_type),
        "payment_ref": event.payment_ref,
        "order_ref": event.order_ref,
        "refund_ref": event.refund_ref,
        "amount": str(event.amount.amount) if event.amount else None,
        "currency": event.currency,
        "instrument": event.instrument.value if event.instrument else None,
        "failure_code": _clean_code(event.failure_code),
        "account_ref": event.account_ref,
        "onboarding_status": event.onboarding_status.value if event.onboarding_status else None,
        "settlement_status": event.settlement_status,
    }


def observation_status(observed: ProviderPayment) -> LedgerStatus:
    """Collapse refund-progress statuses: the ledger tracks refunds on their own rows."""

    return LedgerStatus.captured if observed.status in _SETTLED_STATUSES else observed.status


async def apply_provider_payment(
    repository: PaymentRepository, provider: str, order_ref: str, observed: ProviderPayment
) -> str:
    """Fold a fetched provider payment into the ledger (shared by confirm, refresh, reconcile)."""

    return await repository.apply_payment_observation(
        provider=provider,
        order_ref=order_ref,
        payment_ref=observed.payment_ref,
        status=observation_status(observed).value,
        amount=observed.amount.amount,
        currency=observed.currency,
        instrument=observed.instrument.value if observed.instrument else None,
        failure_code=_clean_code(observed.failure_code),
    )


@dataclass(frozen=True, slots=True)
class SettlementRegistrationDetails:
    """KYC/bank details for payee registration. Used once in memory, never stored or logged."""

    legal_name: str = field(repr=False)
    contact_email: str = field(repr=False)
    contact_phone: str = field(repr=False)
    account_type: str = field(repr=False)
    business_type: str = field(repr=False)
    pan: str = field(repr=False)
    bank_account_number: str | None = field(default=None, repr=False)
    ifsc: str | None = field(default=None, repr=False)
    upi_id: str | None = field(default=None, repr=False)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
