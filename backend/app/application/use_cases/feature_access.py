"""Super-admin feature access: the Trial/Growth/Premium matrix, salon overrides and plan copy."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.exceptions import ValidationError
from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_super_admin
from app.domain.services.feature_access import AUDIENCES, FeatureOverride


class FeatureAccessStore(Protocol):
    async def catalog(self) -> list[dict[str, Any]]: ...
    async def matrix(self) -> dict[str, dict[str, bool]]: ...
    async def list_overrides(self, salon_id: str) -> list[dict[str, Any]]: ...
    async def plan_content(self) -> dict[str, dict[str, Any]]: ...
    async def save_matrix(self, cells: list[dict[str, Any]], actor_id: str) -> None: ...
    async def update_feature(self, key: str, label: str, description: str) -> None: ...
    async def set_override(
        self, salon_id: str, key: str, enabled: bool, expires_at: datetime | None,
        note: str | None, actor_id: str,
    ) -> None: ...
    async def clear_override(self, salon_id: str, key: str) -> None: ...
    async def save_plan_content(
        self, tier: str, headline: str, description: str, bullets: list[str]
    ) -> None: ...


class FeatureAccessUseCases:
    def __init__(
        self, repository: FeatureAccessStore, clock: Callable[[], datetime] | None = None
    ) -> None:
        self.repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    async def overview(self, actor: Profile) -> dict[str, Any]:
        require_super_admin(actor)
        matrix = await self.repository.matrix()
        features = [
            {**row, "access": {a: matrix[row["key"]][a] for a in AUDIENCES}}
            for row in await self.repository.catalog()
        ]
        return {"features": features, "plan_content": await self.repository.plan_content()}

    async def save_matrix(self, actor: Profile, cells: list[dict[str, Any]]) -> dict[str, Any]:
        require_super_admin(actor)
        await self.repository.save_matrix(cells, str(actor.id))
        return await self.overview(actor)

    async def update_feature(
        self, actor: Profile, key: str, label: str, description: str
    ) -> dict[str, Any]:
        require_super_admin(actor)
        if not label.strip():
            raise ValidationError("A feature needs a name")
        await self.repository.update_feature(key, label.strip(), description.strip())
        return await self.overview(actor)

    async def save_plan_content(
        self, actor: Profile, tier: str, headline: str, description: str, bullets: list[str]
    ) -> dict[str, Any]:
        require_super_admin(actor)
        cleaned = [b.strip() for b in bullets if b.strip()]
        await self.repository.save_plan_content(tier, headline.strip(), description.strip(), cleaned)
        return await self.overview(actor)

    async def list_overrides(self, actor: Profile, salon_id: str) -> list[dict[str, Any]]:
        require_super_admin(actor)
        return await self.repository.list_overrides(salon_id)

    async def set_override(
        self, actor: Profile, salon_id: str, key: str, enabled: bool,
        expires_at: datetime | None, note: str | None,
    ) -> list[dict[str, Any]]:
        require_super_admin(actor)
        if expires_at is not None:
            if expires_at.tzinfo is None:
                raise ValidationError("The end date must include a time zone")
            if not FeatureOverride(enabled, expires_at).live(self._clock()):
                raise ValidationError("The end date must be in the future")
        await self.repository.set_override(
            salon_id, key, enabled, expires_at, (note or "").strip() or None, str(actor.id)
        )
        return await self.repository.list_overrides(salon_id)

    async def clear_override(self, actor: Profile, salon_id: str, key: str) -> list[dict[str, Any]]:
        require_super_admin(actor)
        await self.repository.clear_override(salon_id, key)
        return await self.repository.list_overrides(salon_id)
