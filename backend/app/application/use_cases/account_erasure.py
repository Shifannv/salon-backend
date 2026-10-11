"""Idempotent, resumable erasure of a confirmed account-deletion request.

Order (every step recorded in ``step_state``; a retry resumes after the last one):

owner only    bookings_cancelled -> refunds_issued -> refunds_settled
everyone      auth_banned -> db_erased -> media_deleted -> cache_cleared -> auth_deleted
              -> staff_auth_deleted -> verify -> complete

Nothing destructive starts before customers have been told, future bookings cancelled and
refunds settled (or given up on, loudly, after the retry cap).
"""

import hashlib
import logging
import re
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

from app.application.ports.account_deletion_repository import AccountDeletionRepository
from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.cache_gateway import CacheGateway
from app.application.ports.media_references import MediaReferences
from app.application.ports.payment_gateway import PaymentGateway, RefundRequest
from app.application.ports.storage_gateway import StorageGateway
from app.domain.entities.payment import GatewayCapability, RefundStatus
from app.domain.value_objects.money import Money

logger = logging.getLogger(__name__)

MEDIA_NAMESPACES = ("avatars/", "salon-images/", "staff-photos/")
CLOSURE_REFUND_KEY = "salon_closed"


class ErasureVerificationError(RuntimeError):
    """Post-conditions did not hold; the request is retried, never completed."""


class RefundsPendingError(RuntimeError):
    """Closure refunds are still with the provider; wait (not a failure)."""


def closure_refund_provider_key(payment_id: str) -> str:
    """Deterministic provider idempotency key: a retry can never refund twice."""

    return hashlib.sha256(f"{payment_id}:{CLOSURE_REFUND_KEY}".encode()).hexdigest()[:40]


def phone_key_variants(phone: str | None) -> list[str]:
    """Spellings under which a phone number can appear inside a cache key."""

    if not phone:
        return []
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 6:
        return []
    return list(dict.fromkeys([phone.strip(), "+" + digits, digits]))


def managed_media_path(storage: StorageGateway, bucket: str, url: str) -> str | None:
    """Map a stored URL to an object key inside the platform's own namespaces."""

    for namespace in MEDIA_NAMESPACES:
        prefix = storage.get_public_url(bucket, namespace)
        if not url.startswith(prefix):
            continue
        rest = url[len(prefix):]
        parts = rest.split("/")
        if not rest or any(c in rest for c in ("%", "\\", "?", "#")):
            return None
        if any(p in ("", ".", "..") for p in parts):
            return None
        return namespace + rest
    return None


class AccountErasureService:
    """Runs each erasure step once, recording progress so retries resume safely."""

    def __init__(
        self,
        repository: AccountDeletionRepository,
        auth_admin: AuthAdminGateway,
        storage: StorageGateway,
        cache: CacheGateway,
        media_references: MediaReferences,
        release_media_lock: Callable[[], Awaitable[None]],
        bucket: str | None,
        stale_seconds: int,
        *,
        payment_gateway: PaymentGateway | None = None,
        refund_max_attempts: int = 8,
        storage_required: bool = False,
        cache_required: bool = False,
    ) -> None:
        self.repository = repository
        self.auth_admin = auth_admin
        self.storage = storage
        self.cache = cache
        self.media_references = media_references
        self.release_media_lock = release_media_lock
        self.bucket = bucket
        self.stale_seconds = stale_seconds
        self.payment_gateway = payment_gateway
        self.refund_max_attempts = refund_max_attempts
        self.storage_required = storage_required
        self.cache_required = cache_required

    async def process_next(self) -> bool:
        """Claim and run one due request. Returns False when nothing was due."""

        request = await self.repository.claim_due_request(self.stale_seconds)
        if request is None:
            return False
        request_id = str(request["id"])
        delay = min(3600, 30 * 2 ** min(int(request["attempts"]), 7))
        try:
            await self._run(request)
        except RefundsPendingError:
            logger.info("Account erasure %s is waiting for refunds to settle", request_id)
            await self.repository.requeue_request(request_id, "refunds_pending", delay)
        except Exception as exc:
            logger.warning(
                "Account erasure step failed for request %s: %s", request_id, type(exc).__name__
            )
            await self.repository.fail_request(request_id, type(exc).__name__, delay)
        return True

    async def _run(self, request: dict[str, Any]) -> None:
        request_id = str(request["id"])
        user_id = str(request["user_id"])
        attempts = int(request["attempts"])
        state: dict[str, Any] = request["step_state"]

        async def once(step: str, action: Callable[[], Awaitable[None]]) -> None:
            if state.get(step):
                return
            await action()
            await self.repository.record_step(request_id, step)
            state[step] = True

        if request["role"] == "owner":
            await once("bookings_cancelled", lambda: self._cancel_bookings(user_id))
            await once("refunds_issued", lambda: self._issue_refunds(user_id, attempts))
            await once("refunds_settled", lambda: self._settle_refunds(user_id, attempts))

        staff_ids: list[str] = list(state.get("staff_profile_ids", []))
        salon_ids: list[object | None] = list(state.get("salon_ids") or [request.get("salon_id")])
        await once("auth_banned", lambda: self._ban(user_id, staff_ids))
        await once(
            "db_erased", lambda: self.repository.erase_database(user_id, request["role"], staff_ids)
        )
        await once("media_deleted", lambda: self._delete_media(request["media_keys"]))
        await once("cache_cleared", lambda: self._clear_cache(user_id, salon_ids, staff_ids))
        await once("auth_deleted", lambda: self.auth_admin.delete_user(user_id))
        await once("staff_auth_deleted", lambda: self._delete_staff_auth(staff_ids))

        if await self.repository.profile_exists(user_id):
            raise ErasureVerificationError("profile_still_exists")
        if await self.auth_admin.get_user(user_id) is not None:
            raise ErasureVerificationError("auth_user_still_exists")
        await self.repository.complete_request(request_id)

    # ------------------------------------------------ cancel, refund, settle
    async def _cancel_bookings(self, user_id: str) -> None:
        counts = await self.repository.cancel_open_bookings(user_id)
        logger.info(
            "Salon closure cancelled %s booking(s), notified %s customer(s), resolved %s request(s)",
            counts["cancelled"], counts["notified"], counts["resolved"],
        )

    async def _issue_refunds(self, user_id: str, attempts: int) -> None:
        """Refund captured ONLINE payments on closure-cancelled bookings, once each.

        Cash / manually recorded payments are never touched: the platform did not hold
        that money (the customer notice says so). With no provider there are no online
        payments, so there are no candidates and this is a clean no-op.
        """

        candidates = await self.repository.list_closure_refund_candidates(user_id)
        if not candidates:
            return
        gateway = self.payment_gateway
        can_refund = gateway is not None and gateway.supports(GatewayCapability.refunds)
        for payment in candidates:
            payment_id = str(payment["payment_id"])
            booking_id = str(payment["booking_id"])
            provider = payment["provider"]
            if payment["refund_id"] is not None:
                row = {"id": payment["refund_id"], "status": payment["refund_status"],
                       "refund_ref": payment["refund_ref"], "amount": payment["amount"]}
            else:
                amount = Decimal(payment["amount"]) - Decimal(payment["other_refunded"])
                if amount <= 0:
                    continue
                if not can_refund:
                    logger.error(
                        "Closure refund for payment %s cannot be issued: no refund-capable "
                        "provider is configured. Recorded as failed for the operator.", payment_id)
                    await self.repository.record_failed_closure_refund(
                        payment_id, booking_id, provider, amount, "provider_unavailable")
                    continue
                row = await self.repository.begin_closure_refund(
                    payment_id, booking_id, provider, amount)
            if row["status"] != "created" or row["refund_ref"]:
                continue  # settled, failed, or already accepted by the provider: never twice
            amount = Decimal(row["amount"])
            if not can_refund:
                logger.error("Closure refund for payment %s cannot be issued: no refund-capable "
                             "provider is configured.", payment_id)
                await self.repository.record_failed_closure_refund(
                    payment_id, booking_id, provider, amount, "provider_unavailable")
                continue
            assert gateway is not None
            try:
                result = await gateway.refund(RefundRequest(
                    payment_ref=payment["payment_ref"],
                    amount=Money(amount),
                    idempotency_key=closure_refund_provider_key(payment_id),
                    reason="salon_closed",
                ))
            except Exception as exc:
                if attempts < self.refund_max_attempts:
                    raise
                logger.error(
                    "Closure refund for payment %s could not be issued after %s attempts (%s); "
                    "recorded as failed, erasure proceeds", payment_id, attempts,
                    type(exc).__name__)
                await self.repository.record_failed_closure_refund(
                    payment_id, booking_id, provider, amount, "refund_call_failed")
                continue
            await self.repository.finish_closure_refund(
                str(row["id"]), result.refund_ref, result.status.value, result.failure_code)
            if result.status == RefundStatus.failed:
                logger.error("Provider rejected the closure refund for payment %s (%s)",
                             payment_id, result.failure_code)

    async def _settle_refunds(self, user_id: str, attempts: int) -> None:
        """Wait until no closure refund is still ``created`` at the provider."""

        pending = await self.repository.list_unsettled_closure_refunds(user_id)
        if not pending:
            return
        if attempts < self.refund_max_attempts:
            raise RefundsPendingError(f"{len(pending)} refund(s) unsettled")
        logger.error(
            "Closure refunds still unsettled after %s attempts; erasure proceeds and they stay "
            "'created' for the operator to reconcile: %s", attempts, ", ".join(pending))

    # ------------------------------------------------------------- erasure
    async def _ban(self, user_id: str, staff_profile_ids: list[str]) -> None:
        for target in [user_id, *staff_profile_ids]:
            if await self.auth_admin.get_user(target) is not None:
                await self.auth_admin.ban_user(target)

    async def _delete_media(self, urls: list[str]) -> None:
        if not urls:
            return
        if not self.bucket:
            if self.storage_required:
                raise ErasureVerificationError("storage_not_configured")
            logger.warning("Object storage is not configured; %s media URL(s) not deleted", len(urls))
            return
        for url in urls:
            path = managed_media_path(self.storage, self.bucket, url)
            if path is None:
                continue
            try:
                await self.media_references.lock_media_url(url)
                if not await self.media_references.media_url_is_referenced(url):
                    await self.storage.delete_object(self.bucket, path)
            finally:
                await self.release_media_lock()

    async def _delete_staff_auth(self, staff_ids: list[str]) -> None:
        """Remove the Auth identity of every staff login whose profile was hard-deleted."""

        for staff_id in staff_ids:
            if await self.repository.profile_exists(staff_id):
                continue  # failed the repository guard: stays banned, never deleted
            if await self.auth_admin.get_user(staff_id) is not None:
                await self.auth_admin.delete_user(staff_id)

    async def _clear_cache(
        self, user_id: str, salon_ids: list[object | None], staff_ids: list[str]
    ) -> None:
        """Drop every cache entry that can hold the erased person's data.

        Failures surface (and the step retries): a silently-swallowed Redis error used to
        let this step "succeed" with the data still cached.
        """

        if self.cache_required and not self.cache.available:
            raise ErasureVerificationError("cache_unavailable")
        prefixes: list[str] = []
        for salon_id in dict.fromkeys(str(i) for i in salon_ids if i):
            prefixes.append(f"salon:{salon_id}:")
        if prefixes:
            prefixes.append("walkin:qr:")
        for actor in (user_id, *staff_ids):
            prefixes.append(f"idempotency:walkin:v2:{actor}:")
        prefixes.append(f"idempotency:booking:{user_id}:")
        contacts = await self.auth_admin.get_user(user_id)
        for variant in phone_key_variants(contacts.phone if contacts else None):
            prefixes.append(f"rate:otp:{variant}")
        for prefix in prefixes:
            await self.cache.delete_prefix(prefix, strict=True)
