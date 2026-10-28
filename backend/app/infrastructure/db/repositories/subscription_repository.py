"""Subscription repository — SQL persistence for plans, subscriptions, events."""

import hashlib
import json
from collections.abc import Collection
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.db.rows import one_dict_or_none


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

    # ── Per-salon prices ──────────────────────────────────────────────────
    async def list_salon_plan_prices(self, salon_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text("""
                select o.salon_id, o.plan_id, p.code as plan_code,
                       o.price_amount, p.price_amount as default_price_amount,
                       case when p.price_amount > o.price_amount
                            then round((1 - o.price_amount / p.price_amount) * 100)::int
                            else null end as offer_discount_percent,
                       o.set_by, o.updated_at, o.valid_until,
                       (o.valid_until is not null and o.valid_until <= now()) as expired
                from salon_plan_prices o
                join subscription_plans p on p.id = o.plan_id
                where o.salon_id = :salon
                order by p.tier asc, p.code asc
            """),
            {"salon": salon_id},
        )
        return [dict(r) for r in result.mappings().all()]

    async def set_salon_plan_price(
        self,
        salon_id: str,
        plan_id: str,
        price: Decimal,
        actor_id: str,
        valid_until: datetime | None = None,
    ) -> dict[str, Any]:
        """Upsert the price this salon pays for a plan, and record who changed it."""

        if (
            await self.session.execute(text("select 1 from salons where id = :s"), {"s": salon_id})
        ).first() is None:
            raise NotFoundError("Salon not found")
        if (
            await self.session.execute(
                text("select 1 from subscription_plans where id = :p"), {"p": plan_id}
            )
        ).first() is None:
            raise NotFoundError("Subscription plan not found")
        await self.session.execute(
            text("""
                insert into salon_plan_prices (salon_id, plan_id, price_amount, set_by, valid_until)
                values (:salon, :plan, :price, :actor, :until)
                on conflict (salon_id, plan_id) do update
                  set price_amount = excluded.price_amount, set_by = excluded.set_by,
                      valid_until = excluded.valid_until, updated_at = now()
            """),
            {"salon": salon_id, "plan": plan_id, "price": price, "actor": actor_id, "until": valid_until},
        )
        await self._audit("admin_plan_price_set", salon_id, plan_id, str(price), actor_id)
        await self.session.commit()
        rows = [r for r in await self.list_salon_plan_prices(salon_id) if str(r["plan_id"]) == plan_id]
        return rows[0]

    async def clear_salon_plan_price(self, salon_id: str, plan_id: str, actor_id: str) -> None:
        """Go back to the plan's normal price. Idempotent: clearing nothing is not an error."""

        result = await self.session.execute(
            text("delete from salon_plan_prices where salon_id = :s and plan_id = :p returning 1"),
            {"s": salon_id, "p": plan_id},
        )
        if result.first() is not None:
            await self._audit("admin_plan_price_cleared", salon_id, plan_id, None, actor_id)
        await self.session.commit()

    async def _audit(
        self, event_type: str, salon_id: str, plan_id: str, price: str | None, actor_id: str
    ) -> None:
        digest = hashlib.sha256(
            json.dumps(
                {"salon": salon_id, "plan": plan_id, "price": price, "actor": actor_id},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        await self.session.execute(
            text("""
                insert into subscription_events
                  (provider_name, provider_event_reference, event_type, payload_hash,
                   processing_status, processed_at)
                values ('admin', :ref, :type, :hash, 'processed', now())
            """),
            {"ref": f"plan-price:{uuid4()}", "type": event_type, "hash": digest},
        )


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
        self,
        subscription_id: str,
        status: str,
        *,
        allowed_from: Collection[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Move a subscription to ``status``.

        With ``allowed_from`` the UPDATE only matches rows currently in one of those
        states (atomic guard). A miss on an existing row is a no-op when it already
        holds ``status`` (idempotent repeat) and a ``ConflictError`` otherwise.
        """
        extra_sets = "".join(f", {k} = :{k}" for k in kwargs)
        guard = " and cast(status as text) = any(:allowed)" if allowed_from is not None else ""
        params: dict[str, Any] = {"id": subscription_id, "status": status, **kwargs}
        if allowed_from is not None:
            params["allowed"] = [str(s) for s in allowed_from]
        result = await self.session.execute(
            text(f"""
                update salon_subscriptions
                set status = cast(:status as subscription_status){extra_sets}
                where id = :id{guard}
                returning *
            """),
            params,
        )
        row = one_dict_or_none(result)
        if row is not None:
            await self.session.commit()
            return row
        current = one_dict_or_none(
            await self.session.execute(
                text("select * from salon_subscriptions where id = :id"),
                {"id": subscription_id},
            )
        )
        if current is None:
            raise NotFoundError("Subscription not found")
        if str(current["status"]) == str(status):
            return current
        raise ConflictError(
            f"Subscription cannot move from '{current['status']}' to '{status}'"
        )

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
