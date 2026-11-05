"""SQL booking-change adapter. Every business decision is rechecked under DB locks."""

import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BookingChangeError,
    IdempotencyKeyReuseError,
    NotFoundError,
    PayAtSalonDailyLimitError,
    ServiceUnavailableError,
    SlotUnavailableError,
    ValidationError,
)
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

_MESSAGES = {
    "visit_change_requires_full_itinerary": "This visit needs all professionals rescheduled together. Contact the salon to arrange a change.",
    "booking_change_policy_unsupported": "This booking uses an earlier policy and cannot use this change flow.",
    "booking_state_conflict": "Only pending or confirmed bookings can be changed.",
    "booking_change_cutoff": "Services and time can only be changed more than four hours before the appointment.",
    "booking_change_limit": "This booking has already used its two reschedules.",
    "booking_change_version_conflict": "This booking changed. Refresh it before trying again.",
    "booking_change_quote_stale": "The service quote changed. Review the latest price and duration before saving.",
    "booking_change_payment_reconciliation_required": "The recorded payments require reconciliation before changing this booking.",
    "additional_payment_required": "The extra payment must be verified before committing this change.",
    "booking_change_unchanged": "Choose different services, staff or time before saving.",
    "salon_not_accepting_bookings": "This salon is not accepting booking changes right now.",
}


class BookingChangeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _check_single_staff(self, booking_id: str) -> None:
        multi = await self.session.scalar(text("select coalesce((to_jsonb(b)->>'is_multi_staff')::boolean,false) from bookings b where b.id=:id and b.customer_id=auth.uid()"), {"id":booking_id})
        if multi:
            raise BookingChangeError("visit_change_requires_full_itinerary", _MESSAGES["visit_change_requires_full_itinerary"])

    @staticmethod
    def parameters(booking_id: str, values: dict[str, Any]) -> dict[str, Any]:
        return {"booking": booking_id, "staff": str(values["staff_id"]),
                "services": json.dumps([str(s) for s in values["service_ids"]]),
                "start": values["start_datetime"], "version": values["expected_version"]}

    async def availability(self, booking_id: str, staff_id: str, services: list[str], day: date) -> list[dict[str, Any]]:
        await self._check_single_staff(booking_id)
        try:
            result = await self.session.execute(text("""
                with q as materialized (
                  select public.booking_change_quote(cast(:booking as uuid),cast(:staff as uuid),
                    array(select value::uuid from jsonb_array_elements_text(cast(:services as jsonb))),
                    (select start_datetime from public.bookings where id=cast(:booking as uuid))) as value
                ) select g.slot_start,g.slot_end,
                  to_char(g.slot_start at time zone s.timezone,'HH12:MI AM') as id,
                  to_char(g.slot_start at time zone s.timezone,'HH12:MI AM') as time,
                  st.name as "barberName"
                from q cross join public.bookings b
                join public.staff st on st.id=cast(:staff as uuid)
                join public.salons s on s.id=st.salon_id
                cross join lateral public.get_available_slots(st.id,cast(:day as date),
                  (q.value->>'duration_minutes')::integer,cast(:booking as uuid)) g
                where b.id=cast(:booking as uuid) and
                  (b.committed_reschedules < 2 or (g.slot_start=b.start_datetime and st.id=b.staff_id))
            """), {"booking": booking_id, "staff": staff_id, "services": json.dumps(services), "day": day})
            return [dict(row) for row in result.mappings()]
        except DBAPIError as exc:
            await self._failure(exc)
            raise

    async def _failure(self, exc: DBAPIError) -> None:
        await self.session.rollback()
        code = getattr(exc.orig, "sqlstate", None)
        if code in {"42883", "42703", "42P01"}:
            raise ServiceUnavailableError("Booking changes require the reviewed database migration") from exc
        if code in {"23P01", "40P01", "40001"}:
            raise SlotUnavailableError("The booking changed or its slot is no longer available. Refresh and retry.") from exc
        if code not in {"P0001", "23514"}:
            raise exc
        message = str(exc.orig)
        if "booking_not_found" in message:
            raise NotFoundError("Booking not found") from exc
        if "idempotency_key_reused" in message:
            raise IdempotencyKeyReuseError("This Idempotency-Key was already used for another change") from exc
        if "invalid_booking_change" in message:
            raise ValidationError("Choose active services offered by the selected staff member") from exc
        if "pay_at_salon_daily_limit" in message:
            raise PayAtSalonDailyLimitError("You can keep only one active Pay at Salon booking per day") from exc
        if "slot_unavailable" in message:
            raise SlotUnavailableError("Selected slot is no longer available") from exc
        for reason, public in _MESSAGES.items():
            if reason in message:
                raise BookingChangeError(reason, public) from exc
        raise BookingChangeError("booking_change_conflict", "This booking could not be changed") from exc

    async def quote(self, booking_id: str, values: dict[str, Any]) -> dict[str, Any]:
        await self._check_single_staff(booking_id)
        try:
            result = await self.session.scalar(text("""
                select public.booking_change_quote(cast(:booking as uuid),cast(:staff as uuid),
                  array(select value::uuid from jsonb_array_elements_text(cast(:services as jsonb))),
                  cast(:start as timestamptz))::text
            """), self.parameters(booking_id, values))
            row = json.loads(result, parse_float=Decimal)
            if row["version"] != values["expected_version"]:
                raise BookingChangeError("booking_change_version_conflict", _MESSAGES["booking_change_version_conflict"])
            return row
        except DBAPIError as exc:
            await self._failure(exc)
            raise  # _failure always raises; retain an explicit failure path for typing.

    async def commit(self, booking_id: str, values: dict[str, Any], key: str) -> dict[str, Any]:
        await self._check_single_staff(booking_id)
        try:
            await self.session.execute(text("""
                select public.apply_customer_booking_change(cast(:booking as uuid),cast(:staff as uuid),
                  array(select value::uuid from jsonb_array_elements_text(cast(:services as jsonb))),
                  cast(:start as timestamptz),:version,:key,:quote)
            """), {**self.parameters(booking_id, values), "key": key, "quote": values["quote_fingerprint"]})
            actor = await self.session.scalar(text("select auth.uid()::text"))
            row = await PlatformRepository(self.session).get_booking(booking_id, actor)
            if row is None:
                raise NotFoundError("Booking not found")
            await self.session.commit()
            return row
        except DBAPIError as exc:
            await self._failure(exc)
            raise
