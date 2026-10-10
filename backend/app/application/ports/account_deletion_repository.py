"""Account deletion persistence port."""

from abc import ABC, abstractmethod
from typing import Any


class AccountDeletionRepository(ABC):
    """Challenge state, the erasure ledger/outbox, and the erasure transaction."""

    @abstractmethod
    async def count_blockers(self, user_id: str, role: str) -> dict[str, int]:
        """Return open_bookings, pending_requests and active_subscriptions counts."""

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
    async def claim_due_request(self, stale_seconds: int) -> dict[str, Any] | None:
        """Claim one due request for processing (SKIP LOCKED)."""

    @abstractmethod
    async def record_step(self, request_id: str, step: str) -> None:
        """Persist a completed erasure step."""

    @abstractmethod
    async def fail_request(self, request_id: str, error_code: str, delay_seconds: int) -> None:
        """Persist a safe failure code and schedule a retry."""

    @abstractmethod
    async def complete_request(self, request_id: str) -> None:
        """Mark erased and drop the user identifier from the ledger."""

    @abstractmethod
    async def erase_database(self, user_id: str, role: str) -> None:
        """Anonymize retained records and delete the profile in one transaction."""

    @abstractmethod
    async def profile_exists(self, user_id: str) -> bool:
        """Whether a profiles row still exists."""
