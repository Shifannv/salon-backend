"""Owner-side reads and writes for staff earnings: commission rules, who did a service, totals (S1b).

Every statement is scoped by salon id, so another salon's rows are simply not found. Writes are
serialised by the finance salon lock the use case takes first.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError
from app.infrastructure.db.repositories.finance_repository import FinanceRepository, _row

_ATTRIBUTABLE = ("pending", "confirmed", "checked_in")


class StaffEarningsAdminRepository(FinanceRepository):
    async def current_rules(self, salon_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """select distinct on (staff_id, service_id) id, staff_id, service_id, version, commission_type,
                          rate_basis_points, fixed_amount_paise, effective_from, created_at
                   from staff_commission_rule_versions where salon_id = :s
                   order by staff_id nulls first, service_id nulls first, version desc
                   limit 500"""
            ),
            {"s": salon_id},
        )
        return [_row(r) for r in result.mappings().all()]

    async def in_salon(self, salon_id: str, staff_id: str | None, service_id: str | None) -> bool:
        """True when each id that was given is a staff member / service of this salon."""

        if staff_id is not None and not await self.session.scalar(
            text("select 1 from staff where id = :i and salon_id = :s"), {"i": staff_id, "s": salon_id}
        ):
            return False
        return service_id is None or bool(await self.session.scalar(
            text("select 1 from services where id = :i and salon_id = :s"), {"i": service_id, "s": salon_id}
        ))

    async def replay_rule(self, salon_id: str, key: str, request_hash: str) -> dict[str, Any] | None:
        return await self._replay("staff_commission_rule_versions", salon_id, key, request_hash)

    async def latest_start(self, salon_id: str, staff_id: str | None, service_id: str | None) -> datetime | None:
        return await self.session.scalar(
            text(
                """select max(effective_from) from staff_commission_rule_versions
                   where salon_id = :s and staff_id is not distinct from :st and service_id is not distinct from :sv"""
            ),
            {"s": salon_id, "st": staff_id, "sv": service_id},
        )

    async def add_rule(self, values: dict[str, Any]) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                """insert into staff_commission_rule_versions(salon_id, staff_id, service_id, version,
                     commission_type, rate_basis_points, fixed_amount_paise, effective_from, created_by,
                     idempotency_key, request_hash)
                   values(:salon_id, :staff_id, :service_id,
                     (select coalesce(max(version), 0) + 1 from staff_commission_rule_versions
                       where salon_id = :salon_id and staff_id is not distinct from :staff_id
                         and service_id is not distinct from :service_id),
                     :commission_type, :rate_basis_points, :fixed_amount_paise, :effective_from, :created_by,
                     :key, :hash)
                   returning id, staff_id, service_id, version, commission_type, rate_basis_points,
                             fixed_amount_paise, effective_from, created_at"""
            ),
            values,
        )
        return _row(result.mappings().one())

    async def booking_state(self, salon_id: str, booking_id: str, service_id: str) -> str | None:
        """The booking's status when it has this active service line in this salon, else None."""

        return await self.session.scalar(
            text(
                """select b.status::text from bookings b
                   join booking_services bs on bs.booking_id = b.id and bs.service_id = :sv and bs.is_active
                   where b.id = :b and b.salon_id = :s for share of b"""
            ),
            {"b": booking_id, "s": salon_id, "sv": service_id},
        )

    async def set_attribution(
        self, salon_id: str, booking_id: str, service_id: str, staff_id: str, changed_by: str,
    ) -> dict[str, Any]:
        current = await self.session.execute(
            text(
                """select staff_id::text as staff_id, revision from booking_service_staff
                   where booking_id = :b and service_id = :sv order by revision desc limit 1"""
            ),
            {"b": booking_id, "sv": service_id},
        )
        last = current.mappings().first()
        if last is not None and last["staff_id"] == staff_id:  # already them: nothing to record
            return {"booking_id": booking_id, "service_id": service_id, "staff_id": staff_id, "revision": last["revision"]}
        revision = (last["revision"] if last else 0) + 1
        try:
            async with self.session.begin_nested():
                await self.session.execute(
                    text(
                        """insert into booking_service_staff(booking_id, service_id, revision, salon_id, staff_id, changed_by)
                           values(:b, :sv, :r, :s, :st, :by)"""
                    ),
                    {"b": booking_id, "sv": service_id, "r": revision, "s": salon_id, "st": staff_id, "by": changed_by},
                )
        except IntegrityError as error:  # two taps at once: the other one won this revision
            raise ConflictError("This service was just changed; refresh and try again") from error
        return {"booking_id": booking_id, "service_id": service_id, "staff_id": staff_id, "revision": revision}

    async def earnings_by_staff(self, salon_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """select e.staff_id, s.name as staff_name, count(*)::int as services_completed,
                          sum(e.service_value_paise)::bigint as service_value_paise,
                          sum(e.amount_paise)::bigint as commission_paise
                   from staff_earnings e join staff s on s.id = e.staff_id
                   where e.salon_id = :s and e.completed_at >= :a and e.completed_at < :b
                   group by e.staff_id, s.name order by sum(e.amount_paise) desc, s.name"""
            ),
            {"s": salon_id, "a": start, "b": end},
        )
        return [_row(r) for r in result.mappings().all()]


ATTRIBUTABLE_STATUSES = _ATTRIBUTABLE
