"""Subscription use cases — admin-only plan and subscription management."""

from typing import Any

from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Profile, Role
from app.domain.entities.subscription import NON_TERMINAL_STATUSES, SubscriptionStatus
from app.infrastructure.db.repositories.subscription_repository import (
    SalonSubscriptionRepo,
    SubscriptionEventRepo,
    SubscriptionPlanRepo,
)


def _assert_admin(actor: Profile) -> None:
    if actor.role != Role.super_admin:
        raise ForbiddenError("Super admin required")


class SubscriptionPlanUseCases:
    def __init__(self, repo: SubscriptionPlanRepo) -> None:
        self.repo = repo

    async def list_plans(
        self, actor: Profile, *, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        _assert_admin(actor)
        return await self.repo.list_plans(include_inactive=include_inactive)

    async def create_plan(self, actor: Profile, values: dict[str, Any]) -> dict[str, Any]:
        _assert_admin(actor)
        return await self.repo.create_plan(values)

    async def update_plan(
        self, actor: Profile, plan_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        _assert_admin(actor)
        return await self.repo.update_plan(plan_id, values)

    async def deactivate_plan(self, actor: Profile, plan_id: str) -> dict[str, Any]:
        _assert_admin(actor)
        return await self.repo.deactivate_plan(plan_id)


class SalonSubscriptionUseCases:
    def __init__(
        self, repo: SalonSubscriptionRepo, event_repo: SubscriptionEventRepo
    ) -> None:
        self.repo = repo
        self.event_repo = event_repo

    async def get_salon_subscription(
        self, actor: Profile, salon_id: str
    ) -> dict[str, Any] | None:
        _assert_admin(actor)
        return await self.repo.get_salon_subscription(salon_id)

    async def create_test_subscription(
        self, actor: Profile, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Manual/test activation — admin only, labelled as manual."""
        _assert_admin(actor)
        status = values.get("status", "pending")
        if status not in {s.value for s in NON_TERMINAL_STATUSES}:
            raise ValidationError(
                f"Cannot create subscription with terminal status '{status}'"
            )
        return await self.repo.create_subscription(values)

    async def cancel_subscription(
        self, actor: Profile, subscription_id: str
    ) -> dict[str, Any]:
        _assert_admin(actor)
        return await self.repo.update_subscription_status(
            subscription_id, SubscriptionStatus.cancelled
        )

    async def suspend_subscription(
        self, actor: Profile, subscription_id: str
    ) -> dict[str, Any]:
        _assert_admin(actor)
        return await self.repo.update_subscription_status(
            subscription_id, SubscriptionStatus.suspended
        )

    async def list_events(
        self,
        actor: Profile,
        *,
        subscription_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        _assert_admin(actor)
        return await self.event_repo.list_events(
            subscription_id=subscription_id, limit=limit, offset=offset
        )
