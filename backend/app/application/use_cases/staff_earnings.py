"""Staff earnings for the owner: commission rules, who did each service, and what each person earned.

Owner only. Staff never see commission rules or anyone's earnings (decision F02). Rules are versions: a
change is a new row, and what a completed service earned is copied at completion and never rewritten.
Creating a rule or naming who did a service needs an active plan or trial; reading never does.
"""

from __future__ import annotations

import base64
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from app.application.use_cases.finance import MAX_KEY, FinanceUseCases
from app.application.use_cases.idempotency import fingerprint_of, require_idempotency_key
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities.profile import Profile
from app.domain.services.feature_access import SPLIT_BILL, STAFF_EARNINGS
from app.domain.services.finance_ledger import local_day_bounds
from app.infrastructure.db.repositories.staff_earnings_admin_repository import (
    ATTRIBUTABLE_STATUSES,
    StaffEarningsAdminRepository,
)

MAX_START_AHEAD = timedelta(days=366)
START_TOLERANCE = timedelta(minutes=5)
MAX_RANGE_DAYS = 366
DEFAULT_PAGE = 20
MAX_PAGE = 50


def _encode_cursor(completed_at: datetime, booking_id: str, service_id: str) -> str:
    raw = f"{completed_at.astimezone(UTC).isoformat()}|{booking_id}|{service_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str, str]:
    try:
        moment, booking_id, service_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(moment), str(UUID(booking_id)), str(UUID(service_id))
    except (ValueError, UnicodeError) as error:
        raise ValidationError("That page marker is not valid") from error


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
        salon = await self._salon(actor, write=True, feature=STAFF_EARNINGS)
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

    async def service_staff(self, actor: Profile, *, booking_id: str) -> dict[str, Any]:
        salon = await self._salon(actor, feature=SPLIT_BILL)
        found = await self.repository.service_staff(str(salon["id"]), booking_id)
        if found is None:
            raise NotFoundError("Booking not found")
        status, lines = found
        return {"booking_id": booking_id, "lines": lines, "can_change": status in ATTRIBUTABLE_STATUSES and salon["can_write"]}

    async def set_service_staff(
        self, actor: Profile, *, booking_id: str, service_id: str, staff_id: str,
    ) -> dict[str, Any]:
        salon = await self._salon(actor, write=True, feature=SPLIT_BILL)
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

    def _bounds(self, salon: dict[str, Any], from_date: date, to_date: date) -> tuple[datetime, datetime]:
        if to_date < from_date:
            raise ValidationError("The end date is before the start date")
        if (to_date - from_date).days >= MAX_RANGE_DAYS:
            raise ValidationError(f"Choose at most {MAX_RANGE_DAYS} days")
        start, _ = local_day_bounds(from_date, salon["timezone"])
        _, end = local_day_bounds(to_date, salon["timezone"])
        return start, end

    async def earnings(self, actor: Profile, *, from_date: date, to_date: date) -> dict[str, Any]:
        salon = await self._salon(actor, feature=STAFF_EARNINGS)
        start, end = self._bounds(salon, from_date, to_date)
        staff = await self.repository.earnings_by_staff(str(salon["id"]), start, end)
        return {
            "from_date": from_date, "to_date": to_date, "staff": staff,
            "services_completed": sum(s["services_completed"] for s in staff),
            "service_value_paise": sum(s["service_value_paise"] for s in staff),
            "commission_paise": sum(s["commission_paise"] for s in staff),
            "collected_cash_paise": sum(s["collected_cash_paise"] for s in staff),
            "collected_upi_paise": sum(s["collected_upi_paise"] for s in staff),
        }

    async def staff_detail(
        self, actor: Profile, *, staff_id: str, from_date: date, to_date: date,
        cursor: str | None, limit: int = DEFAULT_PAGE,
    ) -> dict[str, Any]:
        """One person's totals for the period and a page of the services they completed."""

        salon = await self._salon(actor, feature=STAFF_EARNINGS)
        salon_id = str(salon["id"])
        start, end = self._bounds(salon, from_date, to_date)
        name = await self.repository.staff_name(salon_id, staff_id)
        if name is None:
            raise NotFoundError("Staff member not found")
        limit = max(1, min(limit, MAX_PAGE))
        after = _decode_cursor(cursor) if cursor else None
        totals = next(iter(await self.repository.earnings_by_staff(salon_id, start, end, staff_id)), None) or {
            "services_completed": 0, "service_value_paise": 0, "commission_paise": 0,
            "collected_cash_paise": 0, "collected_upi_paise": 0,
        }
        rows = await self.repository.staff_history(salon_id, staff_id, start, end, after, limit + 1)
        more = len(rows) > limit
        rows = rows[:limit]
        history = [
            {
                "booking_id": row["booking_id"], "service_id": row["service_id"],
                "service_name": row["service_name"],
                "customer_first_name": (row["customer_name"] or "").strip().split(" ")[0] or "Customer",
                "completed_at": row["completed_at"], "service_value_paise": int(row["service_value_paise"]),
                "commission_paise": int(row["amount_paise"]),
                "booking_cash_paise": row["booking_cash_paise"], "booking_upi_paise": row["booking_upi_paise"],
                "collected_cash_paise": row["collected_cash_paise"], "collected_upi_paise": row["collected_upi_paise"],
                "booking_lines": row["booking_lines"],
            }
            for row in rows
        ]
        last = rows[-1] if rows else None
        return {
            "staff_id": staff_id, "staff_name": name, "from_date": from_date, "to_date": to_date,
            "services_completed": totals["services_completed"], "service_value_paise": totals["service_value_paise"],
            "commission_paise": totals["commission_paise"], "collected_cash_paise": totals["collected_cash_paise"],
            "collected_upi_paise": totals["collected_upi_paise"], "history": history,
            "next_cursor": _encode_cursor(last["completed_at"], last["booking_id"], last["service_id"]) if more and last else None,
        }
