"""Owner wallet and the admin side of payouts.

The owner sees what the platform holds for the salon, asks for a payout on a day, and may take a
waiting request back. The platform admin pays each request by hand and records the bank or UPI
reference, or declines it with a reason. Owner only on the salon side; super admin only on the
admin side. The server computes every figure; a request can never supply a balance. Every owner
write takes the salon lock, so two taps or two devices cannot spend one balance twice, and a payout
request needs an ``Idempotency-Key``: the same key with the same body replays the stored request.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from app.application.use_cases.idempotency import fingerprint_of, require_idempotency_key
from app.core.exceptions import (
    ForbiddenError,
    InsufficientBalanceError,
    NotFoundError,
    PayoutAccountMissingError,
    PayoutAlreadyProcessedError,
    PayoutBelowMinimumError,
    PayoutDayInvalidError,
    PayoutNotCancellableError,
    SalonApprovalRequiredError,
    ValidationError,
)
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import require_super_admin
from app.domain.services.finance_ledger import today_in
from app.domain.services.wallet import (
    MAX_PAYOUT_PAISE,
    MIN_PAYOUT_PAISE,
    PAYOUT_STATUSES,
    PayoutDateProblem,
    available_paise,
    can_cancel,
    check_payout_day,
    net_online_paise,
)

MAX_KEY = 200
MAX_REFERENCE = 100
MIN_REASON = 3
MAX_REASON = 500
DEFAULT_PAGE = 30
MAX_PAGE = 100


def _payout_entry(row: dict[str, Any]) -> dict[str, Any]:
    """A payout request row in the same shape as a wallet history entry."""

    return {
        "id": row["id"],
        "kind": "payout",
        "direction": "debit",
        "amount_paise": int(row["amount_paise"]),
        "status": row["status"],
        "reference": row["reference"],
        "reject_reason": row["reject_reason"],
        "scheduled_for": row["scheduled_for"],
        "can_cancel": can_cancel(row["status"]),
        "created_at": row["created_at"],
    }


def _page_size(limit: int) -> int:
    return max(1, min(limit, MAX_PAGE))


class WalletUseCases:
    def __init__(
        self,
        repository: Any,
        *,
        online_payments_live: bool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self._live = online_payments_live
        self._clock = clock or (lambda: datetime.now(UTC))

    async def _salon(self, actor: Profile) -> dict[str, Any]:
        """The owner's approved salon. Staff and customers never see the wallet."""

        if actor.role is not Role.owner:
            raise ForbiddenError("Salon owner access required")
        salon = await self.repository.owner_salon(actor.id)
        if not salon or not salon["is_active"]:
            raise ForbiddenError("Active salon workspace required")
        if not salon["profile_completed"] or salon["approval_status"] != "approved":
            raise SalonApprovalRequiredError("Super admin approval is required for daily business")
        return salon

    async def _available(self, salon_id: str) -> tuple[int, dict[str, int]]:
        totals = await self.repository.totals(salon_id)
        net = net_online_paise(
            collected=totals["collected"],
            commission=totals["commission"],
            refunded=totals["refunded"],
            commission_reversed=totals["reversed"],
        )
        return available_paise(net_online=net, requested=totals["requested"], paid=totals["paid"]), totals

    async def summary(self, actor: Profile) -> dict[str, Any]:
        salon = await self._salon(actor)
        salon_id = str(salon["id"])
        available, totals = await self._available(salon_id)
        return {
            "available_paise": available,
            "requested_paise": totals["requested"],
            "paid_out_paise": totals["paid"],
            "min_payout_paise": MIN_PAYOUT_PAISE,
            "online_payments_live": self._live,
            "payout_account_ready": await self.repository.payout_account_ready(salon_id),
            "can_request": True,
        }

    async def entries(self, actor: Profile, cursor: str | None, limit: int) -> dict[str, Any]:
        salon = await self._salon(actor)
        rows, next_cursor = await self.repository.entries(str(salon["id"]), cursor, _page_size(limit))
        items = [
            {
                "id": row["id"], "kind": row["kind"], "direction": row["direction"],
                "amount_paise": int(row["amount_paise"]), "status": row["status"],
                "reference": row["reference"], "reject_reason": row["reject_reason"],
                "scheduled_for": row["scheduled_for"], "can_cancel": bool(row["can_cancel"]),
                "created_at": row["happened_at"],
            }
            for row in rows
        ]
        return {"items": items, "next_cursor": next_cursor}

    async def request_payout(
        self, actor: Profile, *, amount_paise: int, scheduled_for: date, idempotency_key: str | None
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key, max_len=MAX_KEY)
        salon = await self._salon(actor)
        salon_id, timezone = str(salon["id"]), salon["timezone"]
        digest = fingerprint_of({"op": "payout", "amount": amount_paise, "day": scheduled_for.isoformat()})
        await self.repository.lock_salon(salon_id)
        # A retry must return the stored request even though the balance has moved on since:
        # look for it before checking anything against today's figures.
        stored = await self.repository.stored_request(salon_id, key, digest)
        if stored is not None:
            return _payout_entry(stored)

        if amount_paise > MAX_PAYOUT_PAISE:
            raise ValidationError("That amount is too large for one payout request")
        if amount_paise < MIN_PAYOUT_PAISE:
            raise PayoutBelowMinimumError("The amount is below the smallest payout")
        try:
            check_payout_day(scheduled_for, today_in(timezone, self._clock()))
        except PayoutDateProblem as error:
            raise PayoutDayInvalidError(str(error)) from error
        if not await self.repository.payout_account_ready(salon_id):
            raise PayoutAccountMissingError("Add your bank or UPI details before asking for a payout")
        available, _ = await self._available(salon_id)
        if amount_paise > available:
            raise InsufficientBalanceError("That is more than is available in your wallet")

        row = await self.repository.add_request({
            "salon_id": salon_id, "amount_paise": amount_paise, "scheduled_for": scheduled_for,
            "requested_by": str(actor.id), "key": key, "hash": digest,
        })
        await self.repository.commit()
        return _payout_entry(row)

    async def cancel_payout(self, actor: Profile, request_id: str) -> dict[str, Any]:
        salon = await self._salon(actor)
        salon_id = str(salon["id"])
        await self.repository.lock_salon(salon_id)
        row = await self.repository.get_request(request_id, salon_id=salon_id, lock=True)
        if row is None:
            raise NotFoundError("Payout request not found")
        if row["status"] == "cancelled":
            return _payout_entry(row)  # a retry of a cancel that already worked
        if not can_cancel(row["status"]):
            raise PayoutNotCancellableError("This payout is already being handled and can no longer be cancelled")
        done = await self.repository.cancel_request(request_id)
        await self.repository.commit()
        return _payout_entry(done)


class WalletAdminUseCases:
    """Super admin: see every request, pay one (with the bank or UPI reference) or decline it."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    async def list_requests(
        self, actor: Profile, *, status: str | None, cursor: str | None, limit: int
    ) -> dict[str, Any]:
        require_super_admin(actor)
        if status is not None and status not in PAYOUT_STATUSES:
            raise ValidationError("Unknown payout status")
        rows, next_cursor = await self.repository.queue(status, cursor, _page_size(limit))
        items = [
            {
                **_payout_entry(row),
                "salon_id": row["salon_id"],
                "salon_name": row["salon_name"],
                "payout_account": {
                    "account_holder_name": row["account_holder_name"],
                    "upi_id": row["upi_id"],
                    "bank_name": row["bank_name"],
                    "bank_account_last4": row["bank_account_last4"],
                    "ifsc": row["ifsc"],
                },
            }
            for row in rows
        ]
        return {"items": items, "next_cursor": next_cursor}

    async def mark_paid(self, actor: Profile, request_id: str, reference: str) -> dict[str, Any]:
        require_super_admin(actor)
        ref = reference.strip()
        if not 1 <= len(ref) <= MAX_REFERENCE:
            raise ValidationError(f"The payment reference must be 1-{MAX_REFERENCE} characters")
        row = await self.repository.get_request(request_id, lock=True)
        if row is None:
            raise NotFoundError("Payout request not found")
        if row["status"] == "paid" and row["reference"] == ref:
            return _payout_entry(row)  # a retry of a payment that already went through
        if row["status"] != "requested":
            raise PayoutAlreadyProcessedError("This payout request has already been handled")
        done = await self.repository.finish_request(
            request_id, status="paid", admin_id=str(actor.id), reference=ref, reject_reason=None
        )
        await self.repository.commit()
        return _payout_entry(done)

    async def reject(self, actor: Profile, request_id: str, reason: str) -> dict[str, Any]:
        require_super_admin(actor)
        why = reason.strip()
        if not MIN_REASON <= len(why) <= MAX_REASON:
            raise ValidationError(f"The reason must be {MIN_REASON}-{MAX_REASON} characters")
        row = await self.repository.get_request(request_id, lock=True)
        if row is None:
            raise NotFoundError("Payout request not found")
        if row["status"] == "rejected" and row["reject_reason"] == why:
            return _payout_entry(row)
        if row["status"] != "requested":
            raise PayoutAlreadyProcessedError("This payout request has already been handled")
        done = await self.repository.finish_request(
            request_id, status="rejected", admin_id=str(actor.id), reference=None, reject_reason=why
        )
        await self.repository.commit()
        return _payout_entry(done)
