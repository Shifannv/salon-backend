"""Super-admin permanent salon deletion.

Three calls, in order of use:

``readiness``  what the salon still owes or is owed (read only).
``prepare``    hide the salon, cancel its open bookings and settle the refunds (auto or manual).
``erase``      remove the salon and everything that hangs off it, once nothing is owed either way.

Money comes first: ``erase`` refuses (409 ``salon_not_ready_for_deletion``) while a refund is due or in
flight or the owner is owed a payout, and checks again inside the transaction that erases. After the
database erase commits, files, cache entries and logins are cleaned up; if that part fails the job stays
``cleanup_pending`` and the same DELETE, repeated, finishes it.
"""

import logging
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any, Literal, Protocol

from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.cache_gateway import CacheGateway
from app.application.ports.media_references import MediaReferences
from app.application.ports.payment_gateway import PaymentGateway, RefundRequest
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.account_erasure import (
    closure_refund_provider_key,
    managed_media_path,
)
from app.core.exceptions import NotFoundError, SalonNotReadyForDeletionError
from app.domain.entities.payment import GatewayCapability, RefundStatus
from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_super_admin
from app.domain.services.wallet import available_paise, net_online_paise
from app.domain.value_objects.money import Money
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

logger = logging.getLogger(__name__)

RefundMode = Literal["auto", "manual"]


class WalletTotals(Protocol):
    async def totals(self, salon_id: str) -> dict[str, int]: ...


class AdminSalonErasureUseCases:
    def __init__(
        self,
        repository: PlatformRepository,
        wallet: WalletTotals,
        auth_admin: AuthAdminGateway,
        storage: StorageGateway,
        cache: CacheGateway,
        media_references: MediaReferences,
        release_media_lock: Callable[[], Awaitable[None]],
        bucket: str | None,
        payment_gateway_for: Callable[[str | None], PaymentGateway | None],
        *,
        storage_required: bool = False,
    ) -> None:
        self.repository = repository
        self.wallet = wallet
        self.auth_admin = auth_admin
        self.storage = storage
        self.cache = cache
        self.media_references = media_references
        self.release_media_lock = release_media_lock
        self.bucket = bucket
        self.payment_gateway_for = payment_gateway_for
        self.storage_required = storage_required

    # ------------------------------------------------------------------ read
    async def readiness(self, actor: Profile, salon_id: str) -> dict[str, Any]:
        require_super_admin(actor)
        return await self._readiness(salon_id)

    async def _readiness(self, salon_id: str) -> dict[str, Any]:
        figures = await self.repository.erasure_figures(salon_id)
        if figures is None:
            raise NotFoundError("Salon not found")
        totals = await self.wallet.totals(salon_id)
        net = net_online_paise(
            collected=totals["collected"],
            commission=totals["commission"],
            refunded=totals["refunded"],
            commission_reversed=totals["reversed"],
        )
        owed = max(0, available_paise(net_online=net, requested=totals["requested"], paid=totals["paid"]))
        blockers = [
            code for code, blocked in (
                ("open_bookings", figures["open_bookings"] > 0),
                ("refunds_due", figures["refunds_due_count"] > 0),
                ("refunds_pending", figures["refunds_pending_count"] > 0),
                ("payout_balance", owed > 0),
                ("payout_requests_pending", figures["payout_requests_pending"] > 0),
            ) if blocked
        ]
        return {
            "salon_id": salon_id,
            **figures,
            "payout_balance_paise": owed,
            "can_delete": not blockers,
            "blockers": blockers,
        }

    # --------------------------------------------------------------- prepare
    async def prepare(self, actor: Profile, salon_id: str, refund_mode: RefundMode) -> dict[str, Any]:
        """Hide the salon, cancel open bookings and settle refunds. Safe to repeat."""

        require_super_admin(actor)
        if await self.repository.erasure_figures(salon_id) is None:
            raise NotFoundError("Salon not found")
        counts = await self.repository.close_salon_for_erasure(salon_id)
        logger.info(
            "Salon %s closed for erasure: cancelled %s booking(s), notified %s customer(s)",
            salon_id, counts["cancelled"], counts["notified"],
        )
        if refund_mode == "manual":
            await self._record_manual_refunds(actor, salon_id)
        else:
            await self._issue_refunds(salon_id)
        return await self._readiness(salon_id)

    async def _record_manual_refunds(self, actor: Profile, salon_id: str) -> None:
        """The admin refunded outside this system: write that down so the ledger agrees."""

        for payment in await self.repository.salon_refund_candidates(salon_id):
            if payment["refund_status"] == "processed":
                continue
            row = await self.repository.record_salon_refund(
                str(payment["payment_id"]), str(payment["booking_id"]), payment["provider"],
                payment["remaining"], status="processed", refund_ref="manual", actor_id=str(actor.id),
            )
            if row["status"] != "processed":
                # A refund row already exists (created or failed) and was refunded by hand instead.
                await self.repository.mark_salon_refund_manual(str(row["id"]))

    async def _issue_refunds(self, salon_id: str) -> None:
        """Refund each captured online payment once, through the provider that holds it."""

        await self.repository.reopen_failed_salon_refunds(salon_id)
        for payment in await self.repository.salon_refund_candidates(salon_id):
            payment_id = str(payment["payment_id"])
            booking_id = str(payment["booking_id"])
            provider = payment["provider"]
            gateway = self.payment_gateway_for(provider)
            can_refund = gateway is not None and gateway.supports(GatewayCapability.refunds)
            amount = Decimal(payment["remaining"])
            if gateway is None or not can_refund:
                row = await self.repository.record_salon_refund(
                    payment_id, booking_id, provider, amount, status="failed", failure_code="provider_unavailable")
                if row["status"] == "created" and not row["refund_ref"]:
                    await self.repository.settle_salon_refund(str(row["id"]), None, "failed", "provider_unavailable")
                continue
            row = await self.repository.record_salon_refund(payment_id, booking_id, provider, amount)
            if row["status"] != "created" or row["refund_ref"]:
                continue  # settled, failed, or already accepted by the provider: never twice
            try:
                result = await gateway.refund(RefundRequest(
                    payment_ref=payment["payment_ref"],
                    amount=Money(Decimal(row["amount"])),
                    idempotency_key=closure_refund_provider_key(payment_id),
                    reason="salon_closed",
                ))
            except Exception as exc:
                logger.error("Refund for payment %s could not be issued (%s)", payment_id, type(exc).__name__)
                await self.repository.settle_salon_refund(str(row["id"]), None, "failed", "refund_call_failed")
                continue
            await self.repository.settle_salon_refund(
                str(row["id"]), result.refund_ref, result.status.value, result.failure_code)
            if result.status == RefundStatus.failed:
                logger.error("Provider rejected the refund for payment %s (%s)", payment_id, result.failure_code)

    # ----------------------------------------------------------------- erase
    async def erase(self, actor: Profile, salon_id: str) -> None:
        require_super_admin(actor)
        job = await self.repository.erasure_job(salon_id)
        if job is not None:
            if job["status"] == "complete":
                raise NotFoundError("Salon not found")
            await self._cleanup(salon_id, job["media_keys"], job["auth_user_ids"])
            return

        # Same transaction from here to the commit inside erase_salon_rows: a refund or payout request
        # that lands after this check waits for the lock and is seen by the erase.
        await self.repository.lock_salon_for_erasure(salon_id)
        state = await self._readiness(salon_id)
        if not state["can_delete"]:
            raise SalonNotReadyForDeletionError(
                "This salon still has money to settle: " + ", ".join(state["blockers"]))
        footprint = await self.repository.erasure_footprint(salon_id)
        candidates = list(dict.fromkeys(
            [*footprint["staff_profile_ids"], *([footprint["owner_id"]] if footprint["owner_id"] else [])]))
        await self.repository.erase_salon_rows(salon_id, footprint["media_urls"], candidates)
        await self._cleanup(salon_id, footprint["media_urls"], candidates)

    async def _cleanup(self, salon_id: str, media_urls: list[str], profile_ids: list[str]) -> None:
        """Files, cache and logins. Every step is repeatable, so a failure is retried by calling erase again."""

        try:
            await self._delete_media(media_urls)
            for prefix in (f"salon:{salon_id}:", "walkin:qr:"):
                await self.cache.delete_prefix(prefix)
            removed = await self.repository.erase_orphan_profiles(profile_ids)
            for profile_id in removed:
                if await self.auth_admin.get_user(profile_id) is not None:
                    await self.auth_admin.delete_user(profile_id)
            await self.repository.finish_erasure_job(salon_id)
        except Exception:
            logger.exception("Salon %s was erased; clean-up of files or logins must be retried", salon_id)

    async def _delete_media(self, urls: list[str]) -> None:
        if not urls:
            return
        if not self.bucket:
            if self.storage_required:
                raise RuntimeError("storage_not_configured")
            logger.warning("Object storage is not configured; %s media URL(s) not deleted", len(urls))
            return
        for url in urls:
            path = managed_media_path(self.storage, self.bucket, url)
            if path is None:
                continue
            try:
                for key in await self.storage.erasure_lock_paths(path):
                    await self.media_references.lock_media_url(self.storage.get_public_url(self.bucket, key))
                paths = await self.storage.erasure_paths(path)
                still_used = False
                for key in paths:
                    if await self.media_references.media_url_is_referenced(self.storage.get_public_url(self.bucket, key)):
                        still_used = True
                        break
                if not still_used:
                    for key in [key for key in paths if key != path] + ([path] if paths else []):
                        await self.storage.delete_object(self.bucket, key)
            finally:
                await self.release_media_lock()
