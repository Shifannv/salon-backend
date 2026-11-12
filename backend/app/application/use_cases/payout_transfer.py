"""Paying a payout automatically through the provider, and following the transfer to its end.

Super admin only. The admin chooses, per request, between paying by hand (``payout_proof``) and
sending the transfer from here. The rules that keep the money safe:

* The transfer row is committed BEFORE the provider is called, so a crash leaves a pending row to look
  up, never an unrecorded transfer.
* One live transfer per request (database unique index) and the request cannot be cancelled, declined
  or paid by hand while one is live (database trigger, plus the checks in the use cases).
* A timeout or 5xx is never "failed": the transfer is looked up by its id. The provider treats our
  ``transfer_id`` as idempotent, so submitting the same id again is the only retry ever made.
* The request becomes ``paid`` only when the provider reports ``SUCCESS``. A failed transfer leaves
  the request waiting, so the admin can send again, pay by hand, or decline.
* The provider is the source of truth. A transfer we recorded as failed that the provider later reports
  as successful still pays the request, and before any new attempt the previous failed one is looked up
  once more, so one payout is never sent twice.
* The same ``apply`` handles the webhook and the admin's Refresh, so both end in the same state.
"""

from __future__ import annotations

import logging
from typing import Any

from app.application.ports.payout_transfer import (
    BeneficiaryRequest,
    PayoutTransferGateway,
    TransferRequest,
    TransferResult,
)
from app.application.use_cases.payout_proof import PayoutNotices
from app.core.exceptions import (
    NotFoundError,
    PayoutAlreadyProcessedError,
    PayoutOutcomeUnknownError,
    PayoutProviderError,
    PayoutProviderUnavailableError,
    PayoutTransferInProgressError,
    PayoutTransferInvalidError,
)
from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_super_admin
from app.domain.services.payout_transfer import (
    TransferProblem,
    beneficiary_id_for,
    choose_mode,
    clean_beneficiary_name,
    map_status,
    normalize_phone,
    transfer_id_for,
)

_log = logging.getLogger(__name__)

MAX_REASON = 200


def _failure_reason(result: TransferResult | None, error: PayoutProviderError | None = None) -> str:
    """A short, safe reason for the admin: the provider's own status code, never its raw text."""

    if error is not None:
        code = (error.details or {}).get("provider_code")
        return str(code or "provider_rejected")[:MAX_REASON]
    if result is None:
        return "provider_rejected"
    return str(result.status_code or result.status or "failed")[:MAX_REASON]


class PayoutTransferUseCases:
    def __init__(
        self,
        repository: Any,
        gateway: PayoutTransferGateway | None,
        *,
        notices: PayoutNotices | None = None,
        beneficiary_secret: str = "",
    ) -> None:
        self.repository = repository
        self._gateway = gateway
        self._notices = notices
        self._beneficiary_secret = beneficiary_secret

    def _provider(self) -> PayoutTransferGateway:
        if self._gateway is None:
            raise PayoutProviderUnavailableError("Automatic payout is not set up. Pay this payout by hand.")
        return self._gateway

    # ------------------------------------------------------------------ send
    async def send(self, actor: Profile, request_id: str) -> None:
        """Start the transfer for one waiting request. The caller reads the detail afterwards."""

        require_super_admin(actor)
        gateway = self._provider()
        row = await self.repository.get_request(request_id, lock=True)
        if row is None:
            raise NotFoundError("Payout request not found")
        if row["status"] != "requested":
            raise PayoutAlreadyProcessedError("This payout request has already been handled")
        if await self.repository.live_transfer(request_id) is not None:
            raise PayoutTransferInProgressError("A payout transfer is already on its way for this payout")
        admin = str(actor.id)
        await self._settle_previous_attempt(request_id, admin)

        salon_id, amount = str(row["salon_id"]), int(row["amount_paise"])
        beneficiary = await self._beneficiary(request_id, salon_id, amount)

        # No money has moved yet: a provider refusal here stores nothing and the admin can retry.
        await gateway.upsert_beneficiary(beneficiary)

        attempt = len(await self.repository.transfers(request_id)) + 1
        transfer_id = transfer_id_for(request_id, attempt)
        await self.repository.add_transfer(
            request_id=request_id, transfer_id=transfer_id, beneficiary_id=beneficiary.beneficiary_id,
            mode=beneficiary.mode, amount_paise=amount, admin_id=admin,
        )
        await self.repository.audit(request_id, "send_transfer", admin)
        await self.repository.commit()  # the pending row exists before the provider can act on it

        await self._submit(
            TransferRequest(
                transfer_id=transfer_id, beneficiary_id=beneficiary.beneficiary_id, amount_paise=amount,
                mode=beneficiary.mode, remarks=f"Salon payout {request_id[:8]}",
            ),
            admin_id=admin,
        )

    async def _settle_previous_attempt(self, request_id: str, admin_id: str) -> None:
        """Before a new attempt, ask once more about the last failed one: money must never go out twice."""

        for earlier in await self.repository.transfers(request_id):
            if earlier["status"] != "failed":
                continue
            seen = await self._provider().get_transfer(earlier["transfer_id"])
            if seen is not None and map_status(seen.status) != "failed":
                await self.apply(seen, admin_id=admin_id)
                raise PayoutTransferInProgressError(
                    "An earlier transfer for this payout was not actually a failure. Check its status first."
                )

    async def _beneficiary(self, request_id: str, salon_id: str, amount: int) -> BeneficiaryRequest:
        account = await self.repository.payout_account_for_request(request_id)
        if account is None:
            raise PayoutTransferInvalidError("This salon has not saved a payout account")
        if account.get("changed_since_request"):
            raise PayoutTransferInvalidError(
                "The owner changed their payout account after asking for this payout. Check the new details "
                "and pay by hand, or ask the owner to request again."
            )
        contact = await self.repository.owner_contact(salon_id)
        phone = normalize_phone((contact or {}).get("phone"))
        if phone is None:
            raise PayoutTransferInvalidError(
                "The salon owner has no valid 10-digit phone number on their profile. Add one, or pay by hand."
            )
        upi = (account.get("upi_id") or "").strip() or None
        number = (account.get("bank_account_number") or "").strip() or None
        ifsc = (account.get("ifsc") or "").strip().upper() or None
        try:
            mode = choose_mode(amount, has_upi=upi is not None, has_bank=bool(number and ifsc))
        except TransferProblem as error:
            raise PayoutTransferInvalidError(str(error)) from None
        identity = upi if mode == "upi" else f"{number}|{ifsc}"
        return BeneficiaryRequest(
            beneficiary_id=beneficiary_id_for(salon_id, str(identity), self._beneficiary_secret),
            name=clean_beneficiary_name(account.get("account_holder_name") or (contact or {}).get("full_name")),
            phone=phone, mode=mode,
            vpa=upi if mode == "upi" else None,
            bank_account_number=number if mode == "imps" else None,
            ifsc=ifsc if mode == "imps" else None,
        )

    async def _submit(self, request: TransferRequest, *, admin_id: str | None) -> None:
        """Send (or re-send, same id) one transfer and apply what comes back."""

        gateway = self._provider()
        try:
            result: TransferResult | None = await gateway.create_transfer(request)
        except PayoutOutcomeUnknownError:
            # It may or may not have been created: ask by id. Never mark it failed on a guess.
            try:
                result = await gateway.get_transfer(request.transfer_id)
            except PayoutProviderError:
                _log.warning("Payout transfer %s outcome unknown; left pending", request.transfer_id)
                return
        except PayoutProviderError as error:
            # A refusal is not proof that nothing was created (a provider may answer a duplicate with a 4xx).
            # Record "failed" only when the provider confirms it holds no such transfer.
            try:
                seen = await gateway.get_transfer(request.transfer_id)
            except PayoutProviderError:
                _log.warning("Payout transfer %s refused but not confirmed absent; left pending", request.transfer_id)
                return
            if seen is not None:
                await self.apply(seen, admin_id=admin_id)
                return
            reason = _failure_reason(None, error)
            await self._mark_failed(request.transfer_id, reason, admin_id)
            # A fresh error: only our own short code goes back to the admin, never the provider's answer.
            raise PayoutProviderError(
                "The payout provider did not accept this transfer. The money is still in the owner's wallet.",
                {"failure_reason": reason},
            ) from None
        if result is not None:
            await self.apply(result, admin_id=admin_id)

    async def _mark_failed(self, transfer_id: str, reason: str, admin_id: str | None) -> None:
        row = await self.repository.transfer_by_provider_id(transfer_id)
        if row is None or row["status"] != "pending":
            return
        await self.repository.update_transfer(
            transfer_id, status="failed", provider_status=None, cf_transfer_id=None, utr=None, failure_reason=reason
        )
        await self.repository.audit(str(row["request_id"]), "transfer_failed", admin_id)
        await self.repository.commit()

    # --------------------------------------------------------------- refresh
    async def refresh(self, actor: Profile, request_id: str) -> None:
        """Ask the provider where the latest transfer stands and apply the answer."""

        require_super_admin(actor)
        gateway = self._provider()
        transfers = await self.repository.transfers(request_id)
        if not transfers:
            if await self.repository.get_request(request_id) is None:
                raise NotFoundError("Payout request not found")
            raise NotFoundError("No payout transfer was started for this payout")
        latest = transfers[-1]
        if latest["status"] == "reversed":
            return
        result = await gateway.get_transfer(latest["transfer_id"])
        if result is None and latest["status"] == "pending":
            # The provider has no record: the first call never arrived. Our id is idempotent, so the
            # same id can be submitted again without any risk of paying twice.
            await self._submit(
                TransferRequest(
                    transfer_id=latest["transfer_id"], beneficiary_id=latest["beneficiary_id"],
                    amount_paise=int(latest["amount_paise"]), mode=latest["mode"],
                    remarks=f"Salon payout {request_id[:8]}",
                ),
                admin_id=str(actor.id),
            )
            return
        if result is not None:
            await self.apply(result, admin_id=str(actor.id))

    # ----------------------------------------------------------------- apply
    async def apply(self, result: TransferResult, *, admin_id: str | None) -> None:
        """Move our records to what the provider reports. Safe to repeat; used by webhook and refresh."""

        known = await self.repository.transfer_by_provider_id(result.transfer_id)
        if known is None:
            _log.warning("Payout event for an unknown transfer %s ignored", result.transfer_id[:12])
            return
        request_id = str(known["request_id"])
        # Lock the request first, then re-read the transfer under it: a webhook and a refresh arriving
        # together serialise here and the second one finds the work already done.
        request = await self.repository.get_request(request_id, lock=True)
        transfer = await self.repository.transfer_by_provider_id(result.transfer_id, lock=True)
        if request is None or transfer is None:
            return
        old, new = transfer["status"], map_status(result.status)
        if new == "reversed" and old == "pending":
            new = "failed"  # the bank never took it: the same as a failure for our records

        if new == "pending" or new == old:
            if old == "pending":
                await self.repository.update_transfer(
                    result.transfer_id, status="pending", provider_status=result.status[:60] or None,
                    cf_transfer_id=result.cf_transfer_id, utr=None, failure_reason=None,
                )
                await self.repository.commit()
            return
        if new == "success" and old in ("pending", "failed"):
            await self._succeed(request, transfer, result, admin_id)
        elif (old, new) == ("pending", "failed"):
            await self._record(transfer, result, "failed", "transfer_failed", admin_id)
        elif (old, new) == ("success", "reversed"):
            await self._record(transfer, result, "reversed", "transfer_reversed", admin_id)
            # The wallet is not changed on its own: the admin reviews the reversal and records a correction.
            _log.error("Payout transfer %s was reversed by the bank after success: review it", result.transfer_id)
        else:
            _log.warning("Payout transfer %s: ignored a late %s after %s", result.transfer_id, new, old)

    async def _record(
        self, transfer: dict[str, Any], result: TransferResult, status: str, action: str, admin_id: str | None
    ) -> None:
        await self.repository.update_transfer(
            transfer["transfer_id"], status=status, provider_status=result.status[:60] or None,
            cf_transfer_id=result.cf_transfer_id, utr=None, failure_reason=_failure_reason(result),
        )
        await self.repository.audit(str(transfer["request_id"]), action, admin_id)
        await self.repository.commit()

    async def _succeed(
        self, request: dict[str, Any], transfer: dict[str, Any], result: TransferResult, admin_id: str | None
    ) -> None:
        request_id = str(request["id"])
        live = await self.repository.live_transfer(request_id)
        if request["status"] != "requested" or (live is not None and live["transfer_id"] != transfer["transfer_id"]):
            # Money went out, but the request cannot take it as its payment (already handled, or another
            # attempt is live). Never raise: the provider would retry forever. Record it for the admin.
            await self.repository.audit(request_id, "transfer_conflict", admin_id)
            await self.repository.commit()
            _log.error(
                "Payout transfer %s succeeded but request %s is %s: review it by hand",
                transfer["transfer_id"], request_id, request["status"],
            )
            return
        utr = (result.utr or "").strip() or None
        reference = utr if utr and not await self.repository.reference_taken(utr) else transfer["transfer_id"]
        await self.repository.update_transfer(
            transfer["transfer_id"], status="success", provider_status=result.status[:60] or None,
            cf_transfer_id=result.cf_transfer_id, utr=utr, failure_reason=None,
        )
        await self.repository.add_provider_payment(
            payout_id=request_id, reference=reference, method=transfer["mode"],
            amount_paise=int(transfer["amount_paise"]), transfer_id=transfer["transfer_id"],
        )
        done = await self.repository.finish_request(
            request_id, status="paid", admin_id=admin_id, reference=reference, reject_reason=None
        )
        await self.repository.audit(request_id, "transfer_success", admin_id)
        await self.repository.commit()
        if self._notices is not None:
            await self._notices.paid(str(done["salon_id"]), request_id, int(transfer["amount_paise"]), reference)
