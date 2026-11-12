"""Paying a payout with proof, looking one up, correcting a paid one, and the daily reconciliation.

Super admin only. A payout is paid in one step that records the reference, when and how it was paid,
the amount and a proof file, then moves the request to 'paid' and writes the audit row: all in one
transaction, so there is never a paid payout without proof and never a stored file without a payout.
Retrying the same payment (same reference) returns the stored record.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PayoutAlreadyProcessedError,
    PayoutPaymentInvalidError,
    PayoutProofInvalidError,
    PayoutReferenceUsedError,
    PayoutTransferInProgressError,
    ValidationError,
)
from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_super_admin
from app.domain.services.payout_proof import (
    PaymentProblem,
    check_method,
    check_paid_at,
    check_proof,
    clean_note,
    clean_reason,
    clean_reference,
    needs_adjustment_reason,
)
from app.domain.services.wallet import MAX_PAYOUT_PAISE, can_cancel

_log = logging.getLogger(__name__)

# Payouts are made in India; a "day" in the reconciliation is an Indian calendar day.
PLATFORM_TIMEZONE = "Asia/Kolkata"
MAX_RECONCILIATION_DAYS = 92

Notifier = Callable[..., Awaitable[None]]


def rupees(paise: int) -> str:
    return f"₹{paise / 100:,.2f}"


class PayoutNotices:
    """Tells the owner when a payout is paid or declined. A push problem never undoes the decision."""

    def __init__(self, notify: Notifier, owner_of: Callable[[str], Awaitable[str | None]]) -> None:
        self._notify = notify
        self._owner_of = owner_of

    async def paid(self, salon_id: str, payout_id: str, amount_paise: int, reference: str) -> None:
        await self._send(
            salon_id, payout_id, "paid", "Payout sent",
            f"{rupees(amount_paise)} was paid to your account. Reference {reference}.",
        )

    async def declined(self, salon_id: str, payout_id: str, reason: str) -> None:
        await self._send(
            salon_id, payout_id, "rejected", "Payout declined",
            f"Your payout request was declined: {reason[:200]}. The money is back in your wallet.",
        )

    async def _send(self, salon_id: str, payout_id: str, status: str, title: str, body: str) -> None:
        try:
            owner = await self._owner_of(salon_id)
            if owner:
                await self._notify(
                    user_id=owner, notification_type="payout_update", title=title, body=body,
                    data={"type": "payout_update", "status": status, "payout_id": payout_id},
                )
        except Exception as error:
            _log.warning("Payout push failed for payout %s: %s", payout_id, type(error).__name__)


def _snapshot(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return json.loads(value) if isinstance(value, str | bytes) else dict(value)


def _entry(row: dict[str, Any], payment: dict[str, Any] | None) -> dict[str, Any]:
    """The same shape the owner's wallet history uses, plus when and how it was paid."""

    return {
        "id": row["id"], "kind": "payout", "direction": "debit", "amount_paise": int(row["amount_paise"]),
        "status": row["status"], "reference": row["reference"], "reject_reason": row["reject_reason"],
        "scheduled_for": row["scheduled_for"], "can_cancel": can_cancel(row["status"]),
        "created_at": row["created_at"],
        "paid_at": payment["paid_at"] if payment else None,
        "method": payment["method"] if payment else None,
    }


def _transfer_view(row: dict[str, Any]) -> dict[str, Any]:
    """One transfer as the admin sees it. Never the account."""

    return {
        "transfer_id": row["transfer_id"], "mode": row["mode"], "amount_paise": int(row["amount_paise"]),
        "status": row["status"], "provider_status": row["provider_status"], "utr": row["utr"],
        "failure_reason": row["failure_reason"], "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def _latest_transfer(transfers: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _transfer_view(transfers[-1]) if transfers else None


class PayoutProofUseCases:
    def __init__(
        self, repository: Any, *, notices: PayoutNotices | None = None, clock: Callable[[], datetime] | None = None
    ) -> None:
        self.repository = repository
        self._notices = notices
        self._clock = clock or (lambda: datetime.now(UTC))

    # ------------------------------------------------------------------ pay
    async def pay(
        self,
        actor: Profile,
        request_id: str,
        *,
        reference: str,
        method: str,
        paid_at: datetime,
        amount_paid_paise: int,
        adjustment_reason: str | None,
        note: str | None,
        proof: bytes,
    ) -> dict[str, Any]:
        require_super_admin(actor)
        try:
            ref = clean_reference(reference)
            how = check_method(method)
            text_note = clean_note(note)
        except PaymentProblem as error:
            raise PayoutPaymentInvalidError(str(error)) from None
        if not 0 < amount_paid_paise <= MAX_PAYOUT_PAISE:
            raise PayoutPaymentInvalidError("Enter the amount that was paid")
        try:
            mime = check_proof(proof)
        except PaymentProblem as error:
            raise PayoutProofInvalidError(str(error)) from None

        row = await self.repository.get_request(request_id, lock=True)
        if row is None:
            raise NotFoundError("Payout request not found")
        if row["status"] == "paid":
            existing = await self.repository.payment(request_id)
            if existing and existing["reference"].lower() == ref.lower():
                return _entry(row, existing)  # a retry of a payment that already went through
            raise PayoutAlreadyProcessedError("This payout request has already been handled")
        if row["status"] != "requested":
            raise PayoutAlreadyProcessedError("This payout request has already been handled")
        if await self.repository.live_transfer(request_id) is not None:
            raise PayoutTransferInProgressError(
                "A payout transfer is already on its way for this payout; refresh its status instead"
            )

        try:
            when = check_paid_at(paid_at, requested_at=row["created_at"], now=self._clock())
            reason = clean_reason(
                adjustment_reason,
                required=needs_adjustment_reason(int(row["amount_paise"]), amount_paid_paise),
                what="a different amount was paid",
            )
        except PaymentProblem as error:
            raise PayoutPaymentInvalidError(str(error)) from None
        if await self.repository.reference_taken(ref):
            raise PayoutReferenceUsedError("This payment reference was already used for another payout")

        admin = str(actor.id)
        try:
            proof_id = await self.repository.add_proof(
                mime_type=mime, content=proof, sha256=hashlib.sha256(proof).hexdigest(), admin_id=admin
            )
            await self.repository.add_payment(
                payout_id=request_id, reference=ref, method=how, paid_at=when,
                amount_paid_paise=amount_paid_paise,
                adjustment_reason=reason if amount_paid_paise != int(row["amount_paise"]) else None,
                note=text_note, proof_id=proof_id, admin_id=admin,
            )
        except IntegrityError:
            raise PayoutReferenceUsedError("This payment reference was already used for another payout") from None
        done = await self.repository.finish_request(
            request_id, status="paid", admin_id=admin, reference=ref, reject_reason=None
        )
        await self.repository.audit(request_id, "pay", admin)
        await self.repository.commit()
        if self._notices is not None:
            await self._notices.paid(str(done["salon_id"]), request_id, amount_paid_paise, ref)
        return _entry(done, await self.repository.payment(request_id))

    # --------------------------------------------------------------- detail
    async def detail(self, actor: Profile, request_id: str) -> dict[str, Any]:
        require_super_admin(actor)
        row = await self.repository.request_detail(request_id)
        if row is None:
            raise NotFoundError("Payout request not found")
        payment = await self.repository.payment(request_id)
        transfers = await self.repository.transfers(request_id)
        live = any(t["status"] in ("pending", "success") for t in transfers)
        return {
            **_entry(row, payment),
            "processing": row["status"] == "requested" and live,
            "salon_id": row["salon_id"],
            "salon_name": row["salon_name"],
            "owner_name": row["owner_name"],
            "processed_at": row["processed_at"],
            "payout_account": {
                "account_holder_name": row["account_holder_name"],
                "upi_id": row["upi_id"],
                "bank_name": row["bank_name"],
                "bank_account_last4": row["bank_account_last4"],
                "ifsc": row["ifsc"],
            },
            "balance_at_request": _snapshot(row["balance_snapshot"]),
            "payment": None if payment is None else {
                "reference": payment["reference"], "method": payment["method"],
                "paid_at": payment["paid_at"], "amount_paid_paise": int(payment["amount_paid_paise"]),
                "adjustment_reason": payment["adjustment_reason"], "note": payment["note"],
                "proof_mime": payment["proof_mime"],
                "proof_size": int(payment["proof_size"]) if payment["proof_size"] is not None else None,
                "source": payment["source"],
            },
            "transfer": _latest_transfer(transfers),
            "transfers": [_transfer_view(t) for t in transfers],
            "corrections": [
                {**c, "delta_paise": int(c["delta_paise"])} for c in await self.repository.corrections(request_id)
            ],
            "timeline": await self.repository.audit_trail(request_id),
        }

    # ----------------------------------------------------------------- proof
    async def proof(self, actor: Profile, request_id: str) -> dict[str, Any]:
        require_super_admin(actor)
        file = await self.repository.proof_file(request_id)
        if file is None:
            raise NotFoundError("No payment proof is recorded for this payout")
        if file["redacted_at"] is not None:
            raise NotFoundError("This proof file was removed under the retention rule; the payment record is kept")
        await self.repository.audit(request_id, "view_proof", str(actor.id))
        await self.repository.commit()
        return {"mime_type": file["mime_type"], "content": bytes(file["content"])}

    async def correction_proof(self, actor: Profile, request_id: str, correction_id: str) -> dict[str, Any]:
        require_super_admin(actor)
        file = await self.repository.correction_proof_file(request_id, correction_id)
        if file is None:
            raise NotFoundError("No proof is recorded for this correction")
        if file["redacted_at"] is not None:
            raise NotFoundError("This proof file was removed under the retention rule; the payment record is kept")
        await self.repository.audit(request_id, "view_proof", str(actor.id))
        await self.repository.commit()
        return {"mime_type": file["mime_type"], "content": bytes(file["content"])}

    # ------------------------------------------------------------ correction
    async def correct(
        self, actor: Profile, request_id: str, *, delta_paise: int, reason: str, reference: str, proof: bytes
    ) -> dict[str, Any]:
        """A linked entry that fixes a paid payout. The paid record itself is never changed."""

        require_super_admin(actor)
        try:
            why = clean_reason(reason, required=True, what="the payout is being corrected")
            ref = clean_reference(reference)
        except PaymentProblem as error:
            raise PayoutPaymentInvalidError(str(error)) from None
        if delta_paise == 0 or abs(delta_paise) > MAX_PAYOUT_PAISE:
            raise PayoutPaymentInvalidError("Enter how much the payout was over or under paid")
        try:
            mime = check_proof(proof)
        except PaymentProblem as error:
            raise PayoutProofInvalidError(str(error)) from None
        row = await self.repository.get_request(request_id, lock=True)
        if row is None:
            raise NotFoundError("Payout request not found")
        if row["status"] != "paid":
            raise ConflictError("Only a paid payout can be corrected")
        admin = str(actor.id)
        proof_id = await self.repository.add_proof(
            mime_type=mime, content=proof, sha256=hashlib.sha256(proof).hexdigest(), admin_id=admin
        )
        await self.repository.add_correction(
            payout_id=request_id, delta_paise=delta_paise, reason=why or "", reference=ref,
            proof_id=proof_id, admin_id=admin,
        )
        await self.repository.audit(request_id, "correct", admin)
        await self.repository.commit()
        return await self.detail(actor, request_id)

    # -------------------------------------------------------- reconciliation
    async def reconciliation(self, actor: Profile, start: date, end: date) -> dict[str, Any]:
        """Per Indian calendar day: what was asked for, what was actually paid, and what was declined."""

        require_super_admin(actor)
        if end < start:
            raise ValidationError("The end date cannot be before the start date")
        if (end - start).days + 1 > MAX_RECONCILIATION_DAYS:
            raise ValidationError(f"Choose at most {MAX_RECONCILIATION_DAYS} days")
        zone = ZoneInfo(PLATFORM_TIMEZONE)
        rows = await self.repository.reconciliation(
            datetime.combine(start, time.min, zone), datetime.combine(end + timedelta(days=1), time.min, zone),
            PLATFORM_TIMEZONE,
        )
        days: dict[date, dict[str, int]] = {}
        for offset in range((end - start).days + 1):
            days[start + timedelta(days=offset)] = {
                "requested_count": 0, "requested_paise": 0, "paid_count": 0, "paid_paise": 0,
                "paid_asked_paise": 0, "declined_count": 0, "declined_paise": 0,
            }
        for row in rows:
            bucket = days.get(row["day"])
            if bucket is None:
                continue
            kind = row["kind"]
            bucket[f"{kind}_count"] = int(row["count"])
            bucket[f"{kind}_paise"] = int(row["amount_paise"])
            if kind == "paid":
                bucket["paid_asked_paise"] = int(row["asked_paise"])
        items = [
            {"date": day, **values, "difference_paise": values["paid_paise"] - values["paid_asked_paise"]}
            for day, values in days.items()
        ]
        keys = ("requested_count", "requested_paise", "paid_count", "paid_paise", "paid_asked_paise",
                "declined_count", "declined_paise", "difference_paise")
        return {"items": items, "totals": {key: sum(item[key] for item in items) for key in keys}}
