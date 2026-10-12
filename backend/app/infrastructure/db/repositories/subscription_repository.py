"""Subscription repository — SQL persistence for plans, subscriptions, events."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError


class SubscriptionPlanRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_plans(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        where = "" if include_inactive else "where is_active"
        result = await self.session.execute(text(f"""
            select id, code, name, description, tier, ranking_weight,
                   price_amount, currency, billing_interval, features, tax_inclusive,
                   is_active,
                   created_at, updated_at
            from subscription_plans {where}
            order by tier asc, ranking_weight desc, name asc
        """))
        return [dict(r) for r in result.mappings().all()]

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        result = await self.session.execute(
            text("select * from subscription_plans where id = :id"),
            {"id": plan_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subscription plan not found")
        return dict(row)

    async def create_plan(self, values: dict[str, Any]) -> dict[str, Any]:
        cols = ", ".join(values.keys())
        placeholders = ", ".join(f":{k}" for k in values)
        result = await self.session.execute(
            text(f"""
                insert into subscription_plans ({cols})
                values ({placeholders})
                returning id, code, name, description, tier, ranking_weight,
                          price_amount, currency, billing_interval, features, tax_inclusive,
                   is_active,
                          created_at, updated_at
            """),
            values,
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_plan(self, plan_id: str, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {k: v for k, v in values.items() if v is not None}
        if not allowed:
            return await self.get_plan(plan_id)
        assignments = ", ".join(f"{k} = :{k}" for k in allowed)
        result = await self.session.execute(
            text(f"""
                update subscription_plans set {assignments}
                where id = :plan_id
                returning id, code, name, description, tier, ranking_weight,
                          price_amount, currency, billing_interval, features, tax_inclusive,
                   is_active,
                          created_at, updated_at
            """),
            {**allowed, "plan_id": plan_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subscription plan not found")
        await self.session.commit()
        return dict(row)

    async def deactivate_plan(self, plan_id: str) -> dict[str, Any]:
        return await self.update_plan(plan_id, {"is_active": False})


class SalonSubscriptionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_salon_subscription(self, salon_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("""
                select ss.*, sp.code as plan_code, sp.name as plan_name,
                       sp.tier as plan_tier, sp.ranking_weight as plan_ranking_weight
                from salon_subscriptions ss
                join subscription_plans sp on sp.id = ss.plan_id
                where ss.salon_id = :salon_id
                  and ss.status not in ('expired', 'cancelled', 'suspended')
                order by ss.created_at desc
                limit 1
            """),
            {"salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def create_subscription(self, values: dict[str, Any]) -> dict[str, Any]:
        result = await self.session.execute(
            text("""
                insert into salon_subscriptions
                  (salon_id, plan_id, status, starts_at,
                   current_period_start, current_period_end)
                values (:salon_id, :plan_id, cast(:status as subscription_status),
                        :starts_at, :current_period_start, :current_period_end)
                returning *
            """),
            values,
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_subscription_status(
        self, subscription_id: str, status: str, **kwargs: Any
    ) -> dict[str, Any]:
        extra_sets = "".join(f", {k} = :{k}" for k in kwargs)
        result = await self.session.execute(
            text(f"""
                update salon_subscriptions
                set status = cast(:status as subscription_status){extra_sets}
                where id = :id
                returning *
            """),
            {"id": subscription_id, "status": status, **kwargs},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subscription not found")
        await self.session.commit()
        return dict(row)

    async def get_active_promotion_weight(self, salon_id: str) -> int:
        result = await self.session.execute(
            text("""
                select coalesce(max(sp.ranking_weight), 0)
                from salon_subscriptions ss
                join subscription_plans sp on sp.id = ss.plan_id
                where ss.salon_id = :salon_id
                  and is_subscription_promotion_active(
                        ss.status, ss.current_period_start,
                        ss.current_period_end, ss.grace_period_end)
            """),
            {"salon_id": salon_id},
        )
        return result.scalar_one()


class SubscriptionEventRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_event(self, values: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self.session.execute(
                text("""
                    insert into subscription_events
                      (salon_subscription_id, provider_name, provider_event_reference,
                       event_type, payload_hash)
                    values (:salon_subscription_id, :provider_name,
                            :provider_event_reference, :event_type, :payload_hash)
                    returning *
                """),
                values,
            )
            await self.session.commit()
            return dict(result.mappings().one())
        except Exception as exc:
            if "uq_subscription_events_provider_ref" in str(exc):
                raise ConflictError("Duplicate provider event") from exc
            raise

    async def list_events(
        self, *, subscription_id: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        where = "where salon_subscription_id = :sub_id" if subscription_id else ""
        result = await self.session.execute(
            text(f"""
                select * from subscription_events {where}
                order by received_at desc
                limit :limit offset :offset
            """),
            {"sub_id": subscription_id, "limit": limit, "offset": offset},
        )
        return [dict(r) for r in result.mappings().all()]

    async def mark_event_processed(self, event_id: str) -> None:
        await self.session.execute(
            text("""
                update subscription_events
                set processing_status = 'processed', processed_at = now()
                where id = :id
            """),
            {"id": event_id},
        )
        await self.session.commit()

    async def mark_event_failed(self, event_id: str, error: str) -> None:
        await self.session.execute(
            text("""
                update subscription_events
                set processing_status = 'failed', error_message = :error
                where id = :id
            """),
            {"id": event_id, "error": error},
        )
        await self.session.commit()
