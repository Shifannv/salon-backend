"""Owner wallet and the admin side of payouts.

The owner sees what the platform holds for the salon, asks for a payout on a day, and may take a
waiting request back. The platform admin pays each request by hand and records the bank or UPI
reference, or declines it with a reason. Owner only on the salon side; super admin only on the
admin side. The server computes every figure; a request can never supply a balance. Every owner
write takes the salon lock, so two taps or two devices cannot spend one balance twice, and a payout
request needs an ``Idempotency-Key``: the same key with the same body replays the stored request.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import Any

from app.application.use_cases.idempotency import fingerprint_of, require_idempotency_key
from app.core.exceptions import (
    EntitlementRequiredError,
    ForbiddenError,
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
from app.domain.entities.profile import Profile, Role
from app.domain.services.authorization import require_super_admin
from app.domain.services.feature_access import WALLET, is_enabled
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

_log = logging.getLogger(__name__)

MAX_KEY = 200
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
        "can_cancel": can_cancel(row["status"]) and not row.get("processing"),
        "processing": bool(row.get("processing")),
        "created_at": row["created_at"],
        "paid_at": row.get("paid_at"),
        "method": row.get("method"),
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
        features: Any = None,
    ) -> None:
        self.repository = repository
        self._live = online_payments_live
        self._clock = clock or (lambda: datetime.now(UTC))
        self._features = features

    async def _salon(self, actor: Profile) -> dict[str, Any]:
        """The owner's approved salon. Staff and customers never see the wallet."""

        if actor.role is not Role.owner:
            raise ForbiddenError("Salon owner access required")
        salon = await self.repository.owner_salon(actor.id)
        if not salon or not salon["is_active"]:
            raise ForbiddenError("Active salon workspace required")
        if not salon["profile_completed"] or salon["approval_status"] != "approved":
            raise SalonApprovalRequiredError("Super admin approval is required for daily business")
        if self._features is not None:
            resolved = await self._features.resolve_current(str(salon["id"]), self._clock())
            locked = not is_enabled(resolved, WALLET)
            if locked and resolved.get(WALLET, {}).get("source") != "none":
                raise EntitlementRequiredError("The wallet is not included in your plan")
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

    async def _minimum(self) -> int:
        """The smallest payout: the super admin's setting, else the built-in default."""

        value = await self.repository.min_payout_paise()
        return MIN_PAYOUT_PAISE if value is None else value

    async def summary(self, actor: Profile) -> dict[str, Any]:
        salon = await self._salon(actor)
        minimum = await self._minimum()
        salon_id = str(salon["id"])
        available, totals = await self._available(salon_id)
        return {
            "available_paise": available,
            "requested_paise": totals["requested"],
            "paid_out_paise": totals["paid"],
            "min_payout_paise": minimum,
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
                "processing": bool(row.get("processing")),
                "created_at": row["happened_at"], "paid_at": row.get("paid_at"), "method": row.get("method"),
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
        if amount_paise < await self._minimum():
            raise PayoutBelowMinimumError("The amount is below the smallest payout")
        try:
            check_payout_day(scheduled_for, today_in(timezone, self._clock()))
        except PayoutDateProblem as error:
            raise PayoutDayInvalidError(str(error)) from error
        if not await self.repository.payout_account_ready(salon_id):
            raise PayoutAccountMissingError("Add your bank or UPI details before asking for a payout")
        available, totals = await self._available(salon_id)
        if amount_paise > available:
            raise InsufficientBalanceError("That is more than is available in your wallet")

        # What the platform held at this moment, kept with the request so the commission shown
        # on the payout later is the one that applied then, whatever the rate becomes.
        snapshot = {
            "collected_paise": totals["collected"], "commission_paise": totals["commission"],
            "refunded_paise": totals["refunded"], "commission_reversed_paise": totals["reversed"],
            "available_paise": available,
        }
        row = await self.repository.add_request({
            "salon_id": salon_id, "amount_paise": amount_paise, "scheduled_for": scheduled_for,
            "requested_by": str(actor.id), "key": key, "hash": digest, "snapshot": json.dumps(snapshot),
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
        if await self.repository.live_transfer(request_id) is not None:
            raise PayoutTransferInProgressError("This payout is already on its way and can no longer be cancelled")
        done = await self.repository.cancel_request(request_id)
        await self.repository.commit()
        return _payout_entry(done)


class WalletAdminUseCases:
    """Super admin: see every request, look at the account to pay, or decline one.

    Paying is in ``payout_proof``: a payout cannot be marked paid without its proof.
    """

    def __init__(
        self,
        repository: Any,
        *,
        audit: Callable[[str, str, str], Awaitable[None]] | None = None,
        notices: Any = None,
    ) -> None:
        self.repository = repository
        self._audit = audit
        self._notices = notices

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
                "amount_paid_paise": row.get("amount_paid_paise"),
                "proof_attached": bool(row.get("proof_attached")),
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

    async def reveal_account(self, actor: Profile, request_id: str) -> dict[str, Any]:
        """The full bank or UPI details the admin needs to pay one waiting request.

        Only while the request is still waiting: once it is paid, declined or cancelled the
        details are no longer needed here. Each look is recorded (who, which request) without the
        account itself.
        """

        require_super_admin(actor)
        row = await self.repository.get_request(request_id)
        if row is None:
            raise NotFoundError("Payout request not found")
        if row["status"] != "requested":
            raise PayoutAlreadyProcessedError("This payout request has already been handled")
        account = await self.repository.payout_account_for_request(request_id)
        if account is None:
            raise NotFoundError("This salon has not saved a payout account")
        _log.info("payout account revealed admin=%s request=%s", actor.id, request_id)
        if self._audit is not None:
            await self._audit(request_id, "reveal", str(actor.id))
            await self.repository.commit()
        return {
            "account_holder_name": account["account_holder_name"],
            "upi_id": account["upi_id"],
            "bank_name": account["bank_name"],
            "bank_account_number": account["bank_account_number"],
            "ifsc": account["ifsc"],
            # The owner can edit the account while a request waits: the admin is told, and checks first.
            "changed_since_request": bool(account.get("changed_since_request")),
        }

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
        if await self.repository.live_transfer(request_id) is not None:
            raise PayoutTransferInProgressError("A transfer for this payout is already on its way")
        done = await self.repository.finish_request(
            request_id, status="rejected", admin_id=str(actor.id), reference=None, reject_reason=why
        )
        if self._audit is not None:
            await self._audit(request_id, "decline", str(actor.id))
        await self.repository.commit()
        if self._notices is not None:
            await self._notices.declined(str(done["salon_id"]), request_id, why)
        return _payout_entry(done)
