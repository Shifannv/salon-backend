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
from app.domain.services.staff_earnings import collected_by_staff, split_refund_across_lines
from app.infrastructure.db.repositories.finance_repository import FinanceRepository, _row

_ATTRIBUTABLE = ("pending", "confirmed", "checked_in")
_PAISE = "round({col} * 100)::bigint"
# Mirrors the Daily Ledger: a refund moves a payment out of captured, but the receipt happened.
_RECEIVED = "('captured','partially_refunded','refunded')"


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

    async def staff_name(self, salon_id: str, staff_id: str) -> str | None:
        return await self.session.scalar(
            text("select name from staff where id = :i and salon_id = :s"), {"i": staff_id, "s": salon_id}
        )

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

    async def service_staff(self, salon_id: str, booking_id: str) -> tuple[str, list[dict[str, Any]]] | None:
        """The booking's status and, per active service line, who is doing it now: the latest named
        person, else the booking's own staff member. None when the booking is not in this salon."""

        status = await self.session.scalar(
            text("select status::text from bookings where id = :b and salon_id = :s"), {"b": booking_id, "s": salon_id}
        )
        if status is None:
            return None
        result = await self.session.execute(
            text(
                """select bs.service_id::text as service_id, bs.service_name,
                          coalesce(a.staff_id, b.staff_id)::text as staff_id, s.name as staff_name
                   from bookings b
                   join booking_services bs on bs.booking_id = b.id and bs.is_active
                   left join lateral (
                     select x.staff_id from booking_service_staff x
                     where x.booking_id = bs.booking_id and x.service_id = bs.service_id
                     order by x.revision desc limit 1
                   ) a on true
                   join staff s on s.id = coalesce(a.staff_id, b.staff_id)
                   where b.id = :b and b.salon_id = :s
                   order by bs.service_id"""
            ),
            {"b": booking_id, "s": salon_id},
        )
        return str(status), [dict(r) for r in result.mappings().all()]

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

    async def _lines(self, salon_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
        """Every completed service line in the period, grouped by booking then service (stable order)."""

        result = await self.session.execute(
            text(
                """select e.booking_id::text as booking_id, e.service_id::text as service_id,
                          e.staff_id::text as staff_id, s.name as staff_name, e.service_value_paise,
                          e.amount_paise, e.completed_at
                   from staff_earnings e join staff s on s.id = e.staff_id
                   where e.salon_id = :s and e.completed_at >= :a and e.completed_at < :b
                   order by e.booking_id, e.service_id"""
            ),
            {"s": salon_id, "a": start, "b": end},
        )
        return [dict(r) for r in result.mappings().all()]

    async def _net_receipts(self, salon_id: str, booking_ids: list[str]) -> dict[str, tuple[int, int]]:
        """(cash, UPI) received per booking, net of processed refunds, in paise. Same sources and
        status rules as the Daily Ledger, so the two never disagree about what was collected."""

        if not booking_ids:
            return {}
        params = {"s": salon_id, "ids": booking_ids}
        received = await self.session.execute(
            text(
                f"""select p.booking_id::text as booking_id,
                           coalesce(sum({_PAISE.format(col='p.amount')}) filter (where p.collection_method = 'CASH'), 0)::bigint as cash,
                           coalesce(sum({_PAISE.format(col='p.amount')}) filter (where p.collection_method = 'UPI_DIRECT'), 0)::bigint as upi
                    from booking_payments p
                    where p.salon_id = :s and p.channel = 'manual' and p.status in {_RECEIVED}
                      and p.booking_id = any(cast(:ids as uuid[])) group by p.booking_id"""
            ),
            params,
        )
        refunded = await self.session.execute(
            text(
                f"""select p.booking_id::text as booking_id,
                           coalesce(sum({_PAISE.format(col='r.amount')}) filter (where p.collection_method = 'CASH'), 0)::bigint as cash,
                           coalesce(sum({_PAISE.format(col='r.amount')}) filter (where p.collection_method is distinct from 'CASH'), 0)::bigint as upi
                    from payment_refunds r join booking_payments p on p.id = r.payment_id
                    where p.salon_id = :s and p.channel = 'manual' and r.status = 'processed'
                      and p.booking_id = any(cast(:ids as uuid[])) group by p.booking_id"""
            ),
            params,
        )
        back = {r["booking_id"]: (int(r["cash"]), int(r["upi"])) for r in refunded.mappings().all()}
        net: dict[str, tuple[int, int]] = {}
        for row in received.mappings().all():
            cash_back, upi_back = back.get(row["booking_id"], (0, 0))
            net[row["booking_id"]] = (max(0, int(row["cash"]) - cash_back), max(0, int(row["upi"]) - upi_back))
        return net

    async def earnings_by_staff(
        self, salon_id: str, start: datetime, end: datetime, staff_id: str | None = None,
    ) -> list[dict[str, Any]]:
        lines = await self._lines(salon_id, start, end)
        receipts = await self._net_receipts(salon_id, sorted({line["booking_id"] for line in lines}))
        by_booking: dict[str, list[dict[str, Any]]] = {}
        for line in lines:
            by_booking.setdefault(line["booking_id"], []).append(line)
        people: dict[str, dict[str, Any]] = {}
        for booking_id, booking_lines in by_booking.items():
            cash, upi = receipts.get(booking_id, (0, 0))
            shares = collected_by_staff(
                [(line["staff_id"], int(line["service_value_paise"])) for line in booking_lines],
                cash_paise=cash, upi_paise=upi,
            )
            counted: set[str] = set()
            for line in booking_lines:
                person = people.setdefault(line["staff_id"], {
                    "staff_id": line["staff_id"], "staff_name": line["staff_name"], "services_completed": 0,
                    "service_value_paise": 0, "commission_paise": 0, "collected_cash_paise": 0,
                    "collected_upi_paise": 0,
                })
                person["services_completed"] += 1
                person["service_value_paise"] += int(line["service_value_paise"])
                person["commission_paise"] += int(line["amount_paise"])
                if line["staff_id"] not in counted:  # a person's share of one booking is added once
                    counted.add(line["staff_id"])
                    person["collected_cash_paise"] += shares[line["staff_id"]][0]
                    person["collected_upi_paise"] += shares[line["staff_id"]][1]
        rows = [person for person in people.values() if staff_id is None or person["staff_id"] == staff_id]
        return sorted(rows, key=lambda r: (-r["commission_paise"], r["staff_name"]))

    async def staff_history(
        self, salon_id: str, staff_id: str, start: datetime, end: datetime,
        after: tuple[datetime, str, str] | None, limit: int,
    ) -> list[dict[str, Any]]:
        """One page (newest first) of the services this person completed, with the way the customer paid
        and this service's share of it. The caller asks for ``limit + 1`` to learn whether more exist."""

        cursor = "" if after is None else (
            "and (e.completed_at, e.booking_id, e.service_id) < (:c1, cast(:c2 as uuid), cast(:c3 as uuid))"
        )
        params: dict[str, Any] = {"s": salon_id, "st": staff_id, "a": start, "b": end, "n": limit}
        if after is not None:
            params.update({"c1": after[0], "c2": after[1], "c3": after[2]})
        page = await self.session.execute(
            text(
                f"""select e.booking_id::text as booking_id, e.service_id::text as service_id,
                           e.service_value_paise, e.amount_paise, e.completed_at,
                           bs.service_name, b.customer_name
                    from staff_earnings e
                    join booking_services bs on bs.booking_id = e.booking_id and bs.service_id = e.service_id
                    join bookings b on b.id = e.booking_id
                    where e.salon_id = :s and e.staff_id = :st and e.completed_at >= :a and e.completed_at < :b {cursor}
                    order by e.completed_at desc, e.booking_id desc, e.service_id desc limit :n"""
            ),
            params,
        )
        rows = [dict(r) for r in page.mappings().all()]
        booking_ids = sorted({row["booking_id"] for row in rows})
        if not booking_ids:
            return []
        siblings = await self.session.execute(
            text(
                """select e.booking_id::text as booking_id, e.service_id::text as service_id, s.name as staff_name,
                          bs.service_name, e.service_value_paise
                   from staff_earnings e join staff s on s.id = e.staff_id
                   join booking_services bs on bs.booking_id = e.booking_id and bs.service_id = e.service_id
                   where e.salon_id = :s and e.booking_id = any(cast(:ids as uuid[]))
                   order by e.booking_id, e.service_id"""
            ),
            {"s": salon_id, "ids": booking_ids},
        )
        by_booking: dict[str, list[dict[str, Any]]] = {}
        for line in siblings.mappings().all():
            by_booking.setdefault(line["booking_id"], []).append(dict(line))
        receipts = await self._net_receipts(salon_id, booking_ids)
        for row in rows:
            lines = by_booking[row["booking_id"]]
            cash, upi = receipts.get(row["booking_id"], (0, 0))
            values = [int(line["service_value_paise"]) for line in lines]
            index = next(i for i, line in enumerate(lines) if line["service_id"] == row["service_id"])
            row["collected_cash_paise"] = split_refund_across_lines(cash, values)[index]
            row["collected_upi_paise"] = split_refund_across_lines(upi, values)[index]
            row["booking_cash_paise"], row["booking_upi_paise"] = cash, upi
            row["booking_lines"] = [
                {"service_name": line["service_name"], "staff_name": line["staff_name"],
                 "service_value_paise": int(line["service_value_paise"])}
                for line in lines
            ]
        return rows


ATTRIBUTABLE_STATUSES = _ATTRIBUTABLE
