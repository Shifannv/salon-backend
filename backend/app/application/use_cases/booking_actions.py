"""Booking action-request and salon-closure orchestration."""

from typing import Any

from fastapi import BackgroundTasks

from app.application.use_cases.paging import paging_kwargs
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.domain.entities.profile import Profile, Role
from app.domain.repositories.booking_action_repository import BookingActionRepository


class BookingActionRequestUseCases:
    """Coordinate customer requests and owner/staff decisions."""

    def __init__(self, repository: BookingActionRepository) -> None:
        self.repository = repository

    async def create_customer_request(
        self,
        actor: Profile,
        booking_id: str,
        kind: str,
        reason: str | None,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Create a role- and booking-scoped customer request."""

        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer booking access required")
        item = await self.repository.create_booking_action_request(
            actor.id,
            booking_id,
            kind,
            reason,
            cancellation_cutoff_minutes=(
                settings.customer_cancellation_cutoff_minutes
            ),
            allow_late_cancellation_requests=(
                settings.allow_late_cancellation_requests
            ),
        )
        self._schedule_outbox(item, background_tasks)
        return item

    async def list_requests(
        self,
        actor: Profile,
        request_status: str | None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List requests in an authenticated salon workspace."""

        if actor.role not in {Role.owner, Role.staff}:
            raise ForbiddenError("Salon workspace access required")
        await assert_approved_workspace(self.repository, actor)
        return await self.repository.list_booking_action_requests(
            actor.id, request_status, **paging_kwargs(limit, offset)
        )

    async def respond(
        self,
        actor: Profile,
        request_id: str,
        decision: str,
        reason: str | None,
        background_tasks: BackgroundTasks | None = None,
        *,
        payment_method: str = "cash",
    ) -> dict[str, Any]:
        """Resolve one request as an authorized salon actor."""

        if actor.role not in {Role.owner, Role.staff}:
            raise ForbiddenError("Salon workspace access required")
        await assert_approved_workspace(self.repository, actor)
        extra = {"payment_method": payment_method} if decision == "received" else {}
        item = await self.repository.respond_booking_action_request(
            actor.id, request_id, decision, reason, **extra
        )
        self._schedule_outbox(item, background_tasks)
        return item

    def _schedule_outbox(
        self,
        result: dict[str, Any],
        background_tasks: BackgroundTasks | None,
    ) -> None:
        if background_tasks is None:
            return
        from app.infrastructure.push.outbox_worker import (
            deliver_notification_outbox_event,
        )

        for outbox_id in result.get("_outbox_ids", []):
            background_tasks.add_task(deliver_notification_outbox_event, outbox_id)


class ClosureUseCases:
    """Preview and atomically apply salon holidays or leave."""

    def __init__(self, repository: BookingActionRepository) -> None:
        self.repository = repository

    async def preview(
        self, actor: Profile, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Return the current overlap set without changing state."""

        if actor.role != Role.owner:
            raise ForbiddenError("Salon owner access required")
        await assert_approved_workspace(self.repository, actor)
        rows = await self.repository.preview_closure(actor.id, values)
        return {"affected_count": len(rows), "affected_bookings": rows}

    async def apply(
        self,
        actor: Profile,
        values: dict[str, Any],
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Create a closure and cancel exactly the previewed bookings."""

        if actor.role != Role.owner:
            raise ForbiddenError("Salon owner access required")
        await assert_approved_workspace(self.repository, actor)
        result = await self.repository.apply_closure(actor.id, values)
        if background_tasks is not None:
            from app.infrastructure.push.outbox_worker import (
                deliver_notification_outbox_event,
            )

            for outbox_id in result.get("_outbox_ids", []):
                background_tasks.add_task(deliver_notification_outbox_event, outbox_id)
        return result
