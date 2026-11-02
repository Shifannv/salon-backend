"""Super-admin payment settings (migration 0056): platform commission, minimum payout, salon rates.

Reads feed the pure resolver in ``domain/services/commission_policy``; writes are super-admin only and
are checked by the use case. Every write commits.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError

_SETTINGS = """select commission_rate_percent, commission_base, min_payout_paise, policy_version, updated_at
               from platform_payment_settings where singleton"""


class PaymentSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_settings(self) -> dict[str, Any]:
        result = await self.session.execute(text(_SETTINGS))
        row = result.mappings().first()
        if row is None:  # the migration seeds the row; a missing one is a broken install
            raise NotFoundError("Payment settings are not set up")
        return dict(row)

    async def update_settings(
        self, rate: Decimal | None, base: str | None, min_payout_paise: int, actor_id: str
    ) -> dict[str, Any]:
        await self.session.execute(
            text(
                """update platform_payment_settings
                   set commission_rate_percent = :rate, commission_base = :base,
                       min_payout_paise = :minimum, updated_by = cast(:actor as uuid)
                   where singleton"""
            ),
            {"rate": rate, "base": base, "minimum": min_payout_paise, "actor": actor_id},
        )
        settings = await self.get_settings()
        await self.session.commit()
        return settings

    async def get_override(self, salon_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """select commission_rate_percent, note, updated_at from salon_commission_overrides
                   where salon_id = cast(:s as uuid)"""
            ),
            {"s": salon_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def salon_exists(self, salon_id: str) -> bool:
        result = await self.session.execute(
            text("select 1 from salons where id = cast(:s as uuid)"), {"s": salon_id}
        )
        return result.first() is not None

    async def set_override(self, salon_id: str, rate: Decimal, note: str | None, actor_id: str) -> None:
        await self.session.execute(
            text(
                """insert into salon_commission_overrides (salon_id, commission_rate_percent, note, set_by)
                   values (cast(:s as uuid), :rate, :note, cast(:actor as uuid))
                   on conflict (salon_id) do update
                     set commission_rate_percent = excluded.commission_rate_percent,
                         note = excluded.note, set_by = excluded.set_by, updated_at = now()"""
            ),
            {"s": salon_id, "rate": rate, "note": note, "actor": actor_id},
        )
        await self.session.commit()

    async def clear_override(self, salon_id: str) -> None:
        await self.session.execute(
            text("delete from salon_commission_overrides where salon_id = cast(:s as uuid)"),
            {"s": salon_id},
        )
        await self.session.commit()
