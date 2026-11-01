"""Writes what each completed service earned its staff member (S1a).

Called inside the booking-completion transaction. Safe to call again for the same booking: a service
line is earned once, ever. It never blocks a completion: before migration 0054 exists it does nothing,
and any failure inside it is isolated in a savepoint and logged, so a salon can always finish a service.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.services.staff_earnings import CommissionRule, earned_amount, select_rule

logger = logging.getLogger(__name__)

_TABLES_PRESENT = text(
    """select to_regclass('public.staff_earnings') is not null
       and to_regclass('public.staff_commission_rule_versions') is not null
       and to_regclass('public.booking_service_staff') is not null"""
)

_LINES = text(
    """
    select b.salon_id, b.staff_id as booking_staff_id, coalesce(b.completed_at, now()) as completed_at,
           bs.service_id, round(bs.price * 100)::bigint as value_paise,
           a.staff_id as attributed_staff_id
    from bookings b
    join booking_services bs on bs.booking_id = b.id
    left join lateral (
      select staff_id from booking_service_staff x
      where x.booking_id = bs.booking_id and x.service_id = bs.service_id
      order by x.revision desc limit 1
    ) a on true
    where b.id = :booking_id and b.status = 'completed' and bs.is_active
    order by bs.service_id
    """
)

_RULES = text(
    """
    select id, staff_id, service_id, version, commission_type, rate_basis_points, fixed_amount_paise, effective_from
    from staff_commission_rule_versions where salon_id = :salon_id
    """
)

_INSERT = text(
    """
    insert into staff_earnings(salon_id, booking_id, service_id, staff_id, attribution_source, service_value_paise,
      amount_paise, rule_version_id, commission_type, rate_basis_points, fixed_amount_paise, completed_at)
    values(:salon_id, :booking_id, :service_id, :staff_id, :source, :value, :amount, :rule_id, :type, :bps, :fixed, :completed_at)
    on conflict (booking_id, service_id) do nothing
    """
)


def _rule(row: Any) -> CommissionRule:
    return CommissionRule(
        id=str(row["id"]),
        staff_id=str(row["staff_id"]) if row["staff_id"] else None,
        service_id=str(row["service_id"]) if row["service_id"] else None,
        version=int(row["version"]),
        commission_type=str(row["commission_type"]),
        rate_basis_points=row["rate_basis_points"],
        fixed_amount_paise=row["fixed_amount_paise"],
        effective_from=row["effective_from"],
    )


async def record_staff_earnings(session: AsyncSession, booking_id: str) -> int:
    """Create the earning rows for a completed booking; returns how many were written.

    Isolated in a savepoint: if anything goes wrong the completion carries on and the problem is
    logged, so the earning can be recreated later by calling this again.
    """

    try:
        async with session.begin_nested():
            return await _record(session, booking_id)
    except Exception:  # a commission problem must never stop a service completing
        logger.exception("staff earnings could not be recorded for booking %s", booking_id)
        return 0


async def _record(session: AsyncSession, booking_id: str) -> int:
    if not await session.scalar(_TABLES_PRESENT):
        return 0
    lines = (await session.execute(_LINES, {"booking_id": booking_id})).mappings().all()
    if not lines:
        return 0
    salon_id = lines[0]["salon_id"]
    rules = [_rule(row) for row in (await session.execute(_RULES, {"salon_id": salon_id})).mappings().all()]
    written = 0
    for line in lines:
        staff_id = str(line["attributed_staff_id"] or line["booking_staff_id"])
        completed_at: datetime = line["completed_at"]
        rule = select_rule(rules, staff_id, str(line["service_id"]), completed_at)
        value = int(line["value_paise"])
        amount = earned_amount(rule, value)
        result = await session.execute(
            _INSERT,
            {
                "salon_id": salon_id,
                "booking_id": booking_id,
                "service_id": line["service_id"],
                "staff_id": staff_id,
                "source": "attributed" if line["attributed_staff_id"] else "booking_staff",
                "value": value,
                "amount": amount,
                "rule_id": rule.id if rule and rule.commission_type != "NONE" else None,
                "type": rule.commission_type if rule else "NONE",
                "bps": rule.rate_basis_points if rule and rule.commission_type == "PERCENT_OF_SERVICE_VALUE" else None,
                "fixed": rule.fixed_amount_paise if rule and rule.commission_type == "FIXED_PER_SERVICE" else None,
                "completed_at": completed_at,
            },
        )
        written += result.rowcount or 0
    return written
