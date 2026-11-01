"""Raw-SQL repository for super-admin feature access (migration 0055).

Reads feed the pure resolver in ``domain/services/feature_access``; writes are super-admin only
and are checked by the use case, not here. Callers own the transaction unless a method commits.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.entities.subscription import derive_entitlement
from app.domain.services.feature_access import FeatureOverride, audience_for, resolve_features
from app.domain.services.finance_ledger import TrialState
from app.infrastructure.db.json_utils import decode_json
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)


class FeatureAccessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ reads
    async def catalog(self) -> list[dict[str, Any]]:
        result = await self.session.execute(text(
            "select key, label, description, sort_order from feature_catalog order by sort_order, key"
        ))
        return [dict(r) for r in result.mappings().all()]

    async def matrix(self) -> dict[str, dict[str, bool]]:
        """``{feature: {trial, growth, premium}}``; every catalogue key is present, missing cells are locked."""

        matrix = {row["key"]: {"trial": False, "growth": False, "premium": False} for row in await self.catalog()}
        result = await self.session.execute(text(
            "select feature_key, audience, enabled from feature_plan_access"
        ))
        for row in result.mappings().all():
            if row["feature_key"] in matrix:
                matrix[row["feature_key"]][row["audience"]] = bool(row["enabled"])
        return matrix

    async def overrides(self, salon_id: str) -> dict[str, FeatureOverride]:
        result = await self.session.execute(text(
            "select feature_key, enabled, expires_at from salon_feature_overrides where salon_id=:s"
        ), {"s": salon_id})
        return {
            r["feature_key"]: FeatureOverride(bool(r["enabled"]), r["expires_at"])
            for r in result.mappings().all()
        }

    async def list_overrides(self, salon_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(text("""
            select feature_key, enabled, expires_at, note, updated_at
            from salon_feature_overrides where salon_id=:s order by feature_key
        """), {"s": salon_id})
        return [dict(r) for r in result.mappings().all()]

    async def plan_content(self) -> dict[str, dict[str, Any]]:
        result = await self.session.execute(text(
            "select tier, headline, description, bullets from plan_tier_content"
        ))
        content: dict[str, dict[str, Any]] = {}
        for row in result.mappings().all():
            item = dict(row)
            item["bullets"] = decode_json(item["bullets"]) or []
            content[item.pop("tier")] = item
        return content

    # ----------------------------------------------------------------- writes
    async def save_matrix(self, cells: list[dict[str, Any]], actor_id: str) -> None:
        for cell in cells:
            result = await self.session.execute(text("""
                insert into feature_plan_access(feature_key, audience, enabled, updated_by)
                select :key, :audience, :enabled, :actor
                where exists (select 1 from feature_catalog where key = :key)
                on conflict (feature_key, audience) do update
                  set enabled=excluded.enabled, updated_by=excluded.updated_by, updated_at=now()
                returning feature_key
            """), {"key": cell["feature_key"], "audience": cell["audience"],
                   "enabled": cell["enabled"], "actor": actor_id})
            if result.scalar_one_or_none() is None:
                raise NotFoundError(f"Unknown feature {cell['feature_key']}")
        await self.session.commit()

    async def update_feature(self, key: str, label: str, description: str) -> None:
        result = await self.session.execute(text("""
            update feature_catalog set label=:label, description=:description, updated_at=now()
            where key=:key returning key
        """), {"key": key, "label": label, "description": description})
        if result.scalar_one_or_none() is None:
            raise NotFoundError("Feature not found")
        await self.session.commit()

    async def set_override(
        self, salon_id: str, key: str, enabled: bool, expires_at: datetime | None,
        note: str | None, actor_id: str,
    ) -> None:
        try:
            await self.session.execute(text("""
                insert into salon_feature_overrides(salon_id, feature_key, enabled, expires_at, note, set_by)
                values (:salon, :key, :enabled, :expires, :note, :actor)
                on conflict (salon_id, feature_key) do update
                  set enabled=excluded.enabled, expires_at=excluded.expires_at, note=excluded.note,
                      set_by=excluded.set_by, updated_at=now()
            """), {"salon": salon_id, "key": key, "enabled": enabled, "expires": expires_at,
                   "note": note, "actor": actor_id})
        except Exception:
            await self.session.rollback()
            raise NotFoundError("Salon or feature not found") from None
        await self.session.commit()

    async def clear_override(self, salon_id: str, key: str) -> None:
        await self.session.execute(text(
            "delete from salon_feature_overrides where salon_id=:s and feature_key=:k"
        ), {"s": salon_id, "k": key})
        await self.session.commit()

    async def save_plan_content(self, tier: str, headline: str, description: str, bullets: list[str]) -> None:
        await self.session.execute(text("""
            insert into plan_tier_content(tier, headline, description, bullets)
            values (:tier, :headline, :description, cast(:bullets as jsonb))
            on conflict (tier) do update set headline=excluded.headline,
              description=excluded.description, bullets=excluded.bullets, updated_at=now()
        """), {"tier": tier, "headline": headline, "description": description,
               "bullets": json.dumps(bullets)})
        await self.session.commit()

    async def resolve_for_salon(
        self, salon_id: str, *, entitlement_active: bool, tier: int | None, trial_active: bool, now: datetime
    ) -> dict[str, dict[str, object]]:
        audience = audience_for(entitlement_active=entitlement_active, tier=tier, trial_active=trial_active)
        return resolve_features(
            audience=audience, matrix=await self.matrix(), overrides=await self.overrides(salon_id), now=now
        )

    async def resolve_current(self, salon_id: str, now: datetime) -> dict[str, dict[str, object]]:
        """Resolve from the salon's stored subscription and trial, for callers that have neither loaded."""

        billing = SubscriptionBillingRepository(self.session)
        subscription = await billing.latest_subscription(salon_id)
        entitlement = derive_entitlement(
            status=str(subscription["status"]) if subscription else None,
            period_start=subscription["current_period_start"] if subscription else None,
            period_end=subscription["current_period_end"] if subscription else None,
            grace_end=subscription["grace_period_end"] if subscription else None,
            now=now,
        )
        access = await billing.booking_access(salon_id)
        trial = TrialState(
            started_at=access.get("trial_started_at"),
            ends_at=access.get("trial_ends_at"),
            booking_limit=access.get("trial_booking_limit"),
            bookings_counted=access.get("bookings_counted"),
            limit_reached_at=access.get("trial_limit_reached_at"),
        )
        return await self.resolve_for_salon(
            salon_id,
            entitlement_active=entitlement.active,
            tier=(subscription or {}).get("plan_tier"),
            trial_active=trial.active(now),
            now=now,
        )
