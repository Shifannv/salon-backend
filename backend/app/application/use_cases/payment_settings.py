"""Super-admin payment settings: the commission rate and base, the minimum payout, salon rates.

The rate and base are never defaulted: until an admin sets them, an online payment is refused. A change
applies to new payments only; every payment keeps the rate it was charged at. The minimum payout is
what the owner wallet enforces. Super admin only. Each change is logged (who, old and new values).
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities.profile import Profile
from app.domain.services.authorization import require_super_admin
from app.domain.services.commission_policy import (
    COMMISSION_BASES,
    check_rate,
    resolve_commission_policy,
)
from app.domain.services.wallet import MAX_PAYOUT_PAISE

_log = logging.getLogger(__name__)

MIN_ALLOWED_MINIMUM_PAISE = 100  # Rs 1: a smaller minimum is almost certainly a typo
MAX_NOTE = 200


def _rate(value: Any) -> Decimal:
    try:
        return check_rate(Decimal(str(value)))
    except InvalidOperation:
        raise ValidationError("Enter the commission rate as a percentage, for example 10 or 7.5") from None
    except ValueError as error:
        raise ValidationError(str(error)) from None


class PaymentSettingsUseCases:
    def __init__(self, repository: Any, *, env_rate: Decimal | None, env_base: str | None,
                 env_version: str) -> None:
        self.repository = repository
        self.env_rate, self.env_base, self.env_version = env_rate, env_base, env_version

    def _view(self, row: dict[str, Any], salon_rate: Decimal | None = None) -> dict[str, Any]:
        policy = resolve_commission_policy(
            salon_rate=salon_rate,
            platform_rate=row["commission_rate_percent"],
            platform_base=row["commission_base"],
            platform_version=row["policy_version"],
            env_rate=self.env_rate, env_base=self.env_base, env_version=self.env_version,
        )
        return {
            "commission_rate_percent": row["commission_rate_percent"],
            "commission_base": row["commission_base"],
            "min_payout_paise": row["min_payout_paise"],
            "policy_version": row["policy_version"],
            "updated_at": row["updated_at"],
            "effective_rate_percent": policy.rate_percent if policy else None,
            "effective_base": policy.base if policy else None,
            "effective_source": policy.source if policy else None,
        }

    async def get(self, actor: Profile) -> dict[str, Any]:
        require_super_admin(actor)
        return self._view(await self.repository.get_settings())

    async def update(
        self, actor: Profile, *, rate: Decimal | None, base: str | None, min_payout_paise: int
    ) -> dict[str, Any]:
        require_super_admin(actor)
        if (rate is None) != (base is None):
            raise ValidationError("Set the commission rate and what it is taken from together, or clear both")
        if rate is not None:
            rate = _rate(rate)
        if base is not None and base not in COMMISSION_BASES:
            raise ValidationError("Choose whether the commission is taken from the online amount or the booking total")
        if not MIN_ALLOWED_MINIMUM_PAISE <= min_payout_paise <= MAX_PAYOUT_PAISE:
            raise ValidationError("The minimum payout must be between Rs 1 and Rs 10,00,000")
        before = await self.repository.get_settings()
        row = await self.repository.update_settings(rate, base, min_payout_paise, str(actor.id))
        _log.info(
            "payment settings changed admin=%s rate=%s->%s base=%s->%s minimum=%s->%s",
            actor.id, before["commission_rate_percent"], rate, before["commission_base"], base,
            before["min_payout_paise"], min_payout_paise,
        )
        return self._view(row)

    async def get_salon_rate(self, actor: Profile, salon_id: str) -> dict[str, Any]:
        require_super_admin(actor)
        return await self._salon_view(salon_id)

    async def _salon_view(self, salon_id: str) -> dict[str, Any]:
        if not await self.repository.salon_exists(salon_id):
            raise NotFoundError("Salon not found")
        override = await self.repository.get_override(salon_id)
        row = await self.repository.get_settings()
        view = self._view(row, override["commission_rate_percent"] if override else None)
        return {
            "salon_id": salon_id,
            "commission_rate_percent": override["commission_rate_percent"] if override else None,
            "note": override["note"] if override else None,
            "effective_rate_percent": view["effective_rate_percent"],
            "effective_base": view["effective_base"],
            "effective_source": view["effective_source"],
        }

    async def set_salon_rate(
        self, actor: Profile, salon_id: str, *, rate: Decimal, note: str | None
    ) -> dict[str, Any]:
        require_super_admin(actor)
        rate = _rate(rate)
        clean = (note or "").strip() or None
        if clean is not None and len(clean) > MAX_NOTE:
            raise ValidationError(f"The note can be at most {MAX_NOTE} characters")
        if not await self.repository.salon_exists(salon_id):
            raise NotFoundError("Salon not found")
        await self.repository.set_override(salon_id, rate, clean, str(actor.id))
        _log.info("salon commission rate set admin=%s salon=%s rate=%s", actor.id, salon_id, rate)
        return await self._salon_view(salon_id)

    async def clear_salon_rate(self, actor: Profile, salon_id: str) -> dict[str, Any]:
        require_super_admin(actor)
        if not await self.repository.salon_exists(salon_id):
            raise NotFoundError("Salon not found")
        await self.repository.clear_override(salon_id)
        _log.info("salon commission rate cleared admin=%s salon=%s", actor.id, salon_id)
        return await self._salon_view(salon_id)
