"""Persistence contract for booking action requests and closure workflows."""

from typing import Any, Protocol


class BookingActionRepository(Protocol):
    """Atomic persistence operations for customer/owner booking decisions."""

    async def get_workspace_salon(self, actor_id: str) -> dict[str, Any] | None:
        """Read the salon assigned to an owner or staff member."""

    async def create_booking_action_request(
        self,
        actor_id: str,
        booking_id: str,
        kind: str,
        reason: str | None,
        *,
        cancellation_cutoff_minutes: int,
        allow_late_cancellation_requests: bool,
    ) -> dict[str, Any]:
        """Create one eligible customer request and its owner notification."""

    async def list_booking_action_requests(
        self, actor_id: str, request_status: str | None
    ) -> list[dict[str, Any]]:
        """List action requests scoped to an owner/staff workspace."""

    async def respond_booking_action_request(
        self,
        actor_id: str,
        request_id: str,
        decision: str,
        reason: str | None,
    ) -> dict[str, Any]:
        """Resolve one pending request and apply its booking transition atomically."""

    async def get_notification_outbox_event(
        self, outbox_id: str
    ) -> dict[str, Any] | None:
        """Claim one due persisted push event."""

    async def list_due_notification_outbox_ids(self, limit: int = 50) -> list[str]:
        """Find persisted push events due for an attempt or retry."""

    async def notification_has_failed_delivery(self, notification_id: str) -> bool:
        """Check whether an active device still needs a push retry."""

    async def enqueue_notification(
        self,
        *,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str,
    ) -> str:
        """Persist a notification and outbox event together."""

    async def mark_notification_outbox_processed(self, outbox_id: str) -> None:
        """Mark a successfully attempted push event processed."""

    async def mark_notification_outbox_retry(
        self, outbox_id: str, error: str
    ) -> None:
        """Leave a failed push event pending with a retry time."""

    async def preview_closure(
        self, actor_id: str, values: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Return active bookings overlapping a holiday or leave."""

    async def apply_closure(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create the closure and cancel the confirmed impact set atomically."""
