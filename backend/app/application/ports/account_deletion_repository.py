"""Account deletion persistence port."""

from abc import ABC, abstractmethod
from typing import Any


class AccountDeletionRepository(ABC):
    """Challenge state, the erasure ledger/outbox, and the erasure transaction."""

    @abstractmethod
    async def count_blockers(self, user_id: str, role: str) -> dict[str, int]:
        """Return open_bookings, pending_requests and active_subscriptions counts."""

    @abstractmethod
    async def count_closure_impact(self, user_id: str) -> dict[str, int]:
        """Owner only: bookings_to_cancel and requests_to_resolve if the salons closed now."""

    @abstractmethod
    async def count_recent_challenges(self, user_id: str, window_seconds: int) -> int:
        """Count challenges created for the user inside the window."""

    @abstractmethod
    async def get_live_challenge(self, user_id: str) -> dict[str, Any] | None:
        """Return the user's sent/verified challenge, expiring it first if stale."""

    @abstractmethod
    async def expire_live_challenge(self, user_id: str) -> None:
        """Mark any live challenge expired."""

    @abstractmethod
    async def create_challenge(
        self, user_id: str, channel: str, contact_hash: str, ttl_seconds: int, max_attempts: int,
    ) -> dict[str, Any]:
        """Insert a new challenge."""

    @abstractmethod
    async def resend_challenge(
        self, challenge_id: str, channel: str, contact_hash: str, ttl_seconds: int,
    ) -> dict[str, Any]:
        """Re-arm a sent challenge; attempts are NOT reset."""

    @abstractmethod
    async def get_challenge(self, challenge_id: str, user_id: str) -> dict[str, Any] | None:
        """Return the challenge only if it belongs to the user."""

    @abstractmethod
    async def begin_verify_attempt(self, challenge_id: str, user_id: str) -> dict[str, Any] | None:
        """Atomically spend one attempt; None if not sent, expired or out of attempts."""

    @abstractmethod
    async def expire_challenge(self, challenge_id: str) -> None:
        """Mark a challenge expired (attempts exhausted)."""

    @abstractmethod
    async def mark_verified(
        self, challenge_id: str, user_id: str, confirmation_hash: str, ttl_seconds: int,
    ) -> dict[str, Any] | None:
        """sent -> verified exactly once; None when another request already won."""

    @abstractmethod
    async def confirm_deletion(
        self, user_id: str, challenge_id: str, confirmation_hash: str,
    ) -> dict[str, Any]:
        """Atomically lock out the account and enqueue erasure; idempotent."""

    @abstractmethod
    async def get_request(self, request_id: str) -> dict[str, Any] | None:
        """Return a ledger row."""

    @abstractmethod
    async def list_requests(self, limit: int, offset: int) -> list[dict[str, Any]]:
        """Return ledger rows, newest first, without personal identifiers."""

    @abstractmethod
    async def list_closed_salons(self, limit: int, offset: int) -> list[dict[str, Any]]:
        """Owner deletion ledger rows that closed a salon, newest first, no personal identifiers."""

    @abstractmethod
    async def closed_salon_monthly_statement(self, salon_id: str) -> list[dict[str, Any]] | None:
        """Raw money totals per month and currency for a salon closed by account deletion.

        Returns ``None`` when no owner deletion closed this salon, so the statement can never
        be used to read an active salon's finances.
        """

    @abstractmethod
    async def claim_due_request(self, stale_seconds: int) -> dict[str, Any] | None:
        """Claim one due request for processing (SKIP LOCKED)."""

    @abstractmethod
    async def record_step(self, request_id: str, step: str) -> None:
        """Persist a completed erasure step."""

    @abstractmethod
    async def fail_request(self, request_id: str, error_code: str, delay_seconds: int) -> None:
        """Persist a safe failure code and schedule a retry."""

    @abstractmethod
    async def requeue_request(self, request_id: str, reason_code: str, delay_seconds: int) -> None:
        """Release the claim and retry later WITHOUT marking the request failed."""

    @abstractmethod
    async def cancel_open_bookings(self, user_id: str) -> dict[str, int]:
        """Cancel future bookings at the owner's salons, notify customers, resolve requests.

        Also winds down the salons' subscription billing (cancel renewal, expire unpaid
        orders locally, flag paid-but-unused periods). One transaction; a re-run is a no-op.
        Returns cancelled/notified/resolved counts.
        """

    @abstractmethod
    async def list_closure_refund_candidates(self, user_id: str) -> list[dict[str, Any]]:
        """Online payments on closure-cancelled bookings plus any refund already begun."""

    @abstractmethod
    async def begin_closure_refund(
        self, payment_id: str, booking_id: str, provider: str | None, amount: Any
    ) -> dict[str, Any]:
        """Insert-or-get the one closure refund row for a payment (exactly-once)."""

    @abstractmethod
    async def finish_closure_refund(
        self, refund_id: str, refund_ref: str | None, status: str, failure_code: str | None
    ) -> None:
        """Record the provider's answer for a refund that is still ``created``."""

    @abstractmethod
    async def record_failed_closure_refund(
        self, payment_id: str, booking_id: str, provider: str | None, amount: Any, failure_code: str
    ) -> None:
        """Persist a refund the platform could not issue, for the operator."""

    @abstractmethod
    async def list_unsettled_closure_refunds(self, user_id: str) -> list[str]:
        """Ids of closure refunds still ``created`` (provider has not settled them)."""

    @abstractmethod
    async def complete_request(self, request_id: str) -> None:
        """Mark erased; drop identifiers, step state and the salon snapshot from the ledger."""

    @abstractmethod
    async def erase_database(
        self, user_id: str, role: str, staff_profile_ids: list[str] | None = None
    ) -> None:
        """Anonymize retained records and delete the profile(s) in one transaction.

        ``staff_profile_ids`` are the owner's staff logins; those passing the repository's
        guard are hard-deleted along with the owner. Re-runnable.
        """

    @abstractmethod
    async def profile_exists(self, user_id: str) -> bool:
        """Whether a profiles row still exists."""
