"""Staff earnings for the owner: commission rules, who did each service, and what each person earned.

Owner only. Staff never see commission rules or anyone's earnings (decision F02). Rules are versions: a
change is a new row, and what a completed service earned is copied at completion and never rewritten.
Creating a rule or naming who did a service needs an active plan or trial; reading never does.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.application.use_cases.finance import MAX_KEY, FinanceUseCases
from app.application.use_cases.idempotency import fingerprint_of, require_idempotency_key
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities.profile import Profile
from app.domain.services.finance_ledger import local_day_bounds
from app.infrastructure.db.repositories.staff_earnings_admin_repository import (
    ATTRIBUTABLE_STATUSES,
    StaffEarningsAdminRepository,
)

MAX_START_AHEAD = timedelta(days=366)
START_TOLERANCE = timedelta(minutes=5)
MAX_RANGE_DAYS = 366


class StaffEarningsUseCases(FinanceUseCases):
    repository: StaffEarningsAdminRepository

    async def list_rules(self, actor: Profile) -> dict[str, Any]:
        salon = await self._salon(actor)
        return {"rules": await self.repository.current_rules(str(salon["id"])), "can_write": salon["can_write"]}

    async def add_rule(
        self, actor: Profile, *, staff_id: str | None, service_id: str | None, commission_type: str,
        rate_basis_points: int | None, fixed_amount_paise: int | None, effective_from: datetime | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key, max_len=MAX_KEY)
        salon = await self._salon(actor, write=True)
        salon_id = str(salon["id"])
        now = self._clock()
        start = effective_from.astimezone(UTC) if effective_from else now
        digest = fingerprint_of({
            "op": "commission_rule", "staff": staff_id, "service": service_id, "type": commission_type,
            "bps": rate_basis_points, "fixed": fixed_amount_paise,
            "from": effective_from.astimezone(UTC).isoformat() if effective_from else None,
        })
        await self.repository.lock_salon(salon_id)
        existing = await self.repository.replay_rule(salon_id, key, digest)
        if existing is not None:
            return {**existing, "replayed": True}
        if start < now - START_TOLERANCE or start > now + MAX_START_AHEAD:
            raise ValidationError("A commission rule can start now or up to a year ahead, not in the past")
        if not await self.repository.in_salon(salon_id, staff_id, service_id):
            raise NotFoundError("Staff member or service not found")
        latest = await self.repository.latest_start(salon_id, staff_id, service_id)
        if latest is not None and start < latest:
            raise ConflictError("A rule for this is already scheduled to start later; choose a later start")
        row = await self.repository.add_rule({
            "salon_id": salon_id, "staff_id": staff_id, "service_id": service_id,
            "commission_type": commission_type, "rate_basis_points": rate_basis_points,
            "fixed_amount_paise": fixed_amount_paise, "effective_from": start, "created_by": actor.id,
            "key": key, "hash": digest,
        })
        await self.repository.commit()
        return {**row, "replayed": False}

    async def set_service_staff(
        self, actor: Profile, *, booking_id: str, service_id: str, staff_id: str,
    ) -> dict[str, Any]:
        salon = await self._salon(actor, write=True)
        salon_id = str(salon["id"])
        await self.repository.lock_salon(salon_id)
        status = await self.repository.booking_state(salon_id, booking_id, service_id)
        if status is None:
            raise NotFoundError("Booking service not found")
        if status not in ATTRIBUTABLE_STATUSES:
            raise ConflictError("Who did this service can no longer be changed here once it is finished or closed")
        if not await self.repository.in_salon(salon_id, staff_id, None):
            raise NotFoundError("Staff member not found")
        row = await self.repository.set_attribution(salon_id, booking_id, service_id, staff_id, actor.id)
        await self.repository.commit()
        return row

    async def earnings(self, actor: Profile, *, from_date: date, to_date: date) -> dict[str, Any]:
        salon = await self._salon(actor)
        if to_date < from_date:
            raise ValidationError("The end date is before the start date")
        if (to_date - from_date).days >= MAX_RANGE_DAYS:
            raise ValidationError(f"Choose at most {MAX_RANGE_DAYS} days")
        start, _ = local_day_bounds(from_date, salon["timezone"])
        _, end = local_day_bounds(to_date, salon["timezone"])
        staff = await self.repository.earnings_by_staff(str(salon["id"]), start, end)
        return {
            "from_date": from_date, "to_date": to_date, "staff": staff,
            "services_completed": sum(s["services_completed"] for s in staff),
            "service_value_paise": sum(s["service_value_paise"] for s in staff),
            "commission_paise": sum(s["commission_paise"] for s in staff),
        }
