"""Subscription use cases — admin-only plan and subscription management."""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.exceptions import ForbiddenError, ValidationError
from app.domain.entities.profile import Profile, Role
from app.domain.entities.subscription import NON_TERMINAL_STATUSES, SubscriptionStatus
from app.infrastructure.db.repositories.subscription_repository import (
    SalonSubscriptionRepo,
    SubscriptionEventRepo,
    SubscriptionPlanRepo,
)

# Admin transitions are only valid from these source states; expired and cancelled
# are final, and a repeat of the same transition is a no-op (see the repository).
_CANCEL_FROM = NON_TERMINAL_STATUSES | {SubscriptionStatus.suspended}
_SUSPEND_FROM = NON_TERMINAL_STATUSES


def _assert_admin(actor: Profile) -> None:
    if actor.role != Role.super_admin:
        raise ForbiddenError("Super admin required")


def resolve_offer_price(
    default_price: Decimal, price: Decimal | None, offer_discount_percent: int | None
) -> Decimal:
    """The final offered price for a plan, from either an amount or a percentage off.

    Shared by the single and the bulk offer so both enforce exactly the same rules.
    """

    if (price is None) == (offer_discount_percent is None):
        raise ValidationError("Provide exactly one offer amount or percentage")
    if offer_discount_percent is not None:
        if not 1 <= offer_discount_percent <= 99:
            raise ValidationError("Offer percentage must be between 1 and 99")
        price = (
            default_price * (Decimal(100) - Decimal(offer_discount_percent)) / Decimal(100)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if price is None or price <= 0:
        raise ValidationError("A plan price must be greater than zero")
    if price >= default_price:
        raise ValidationError("An offered price must be below the plan's normal price")
    return price


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

    async def list_salon_prices(self, actor: Profile, salon_id: str) -> list[dict[str, Any]]:
        _assert_admin(actor)
        return await self.repo.list_salon_plan_prices(salon_id)

    async def set_salon_price(
        self,
        actor: Profile,
        salon_id: str,
        plan_id: str,
        price: Decimal | None = None,
        offer_discount_percent: int | None = None,
        valid_until: datetime | None = None,
    ) -> dict[str, Any]:
        _assert_admin(actor)
        if valid_until is not None and valid_until <= datetime.now(UTC):
            raise ValidationError("An offer must end in the future")
        plan = await self.repo.get_plan(plan_id)
        price = resolve_offer_price(
            Decimal(str(plan["price_amount"])), price, offer_discount_percent
        )
        return await self.repo.set_salon_plan_price(
            salon_id, plan_id, price, str(actor.id), valid_until=valid_until
        )

    async def clear_salon_price(self, actor: Profile, salon_id: str, plan_id: str) -> None:
        _assert_admin(actor)
        await self.repo.clear_salon_plan_price(salon_id, plan_id, str(actor.id))


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
            subscription_id,
            SubscriptionStatus.cancelled,
            allowed_from=_CANCEL_FROM,
            cancelled_at=datetime.now(UTC),
        )

    async def suspend_subscription(
        self, actor: Profile, subscription_id: str
    ) -> dict[str, Any]:
        _assert_admin(actor)
        return await self.repo.update_subscription_status(
            subscription_id, SubscriptionStatus.suspended, allowed_from=_SUSPEND_FROM
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
