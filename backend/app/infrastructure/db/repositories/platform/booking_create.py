"""Availability, quoting and booking creation."""

import json
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AppError,
    BookingIdempotencyKeyReusedError,
    ConflictError,
    IdempotencyKeyReuseError,
    NotFoundError,
    ValidationError,
)
from app.infrastructure.db.repositories.platform._sql import (
    _CREATE_BOOKING_ERROR_RULES,
    _error_for_message,
    _is_business_error,
    _request_fingerprint,
)


class BookingCreateMixin:
    """Availability, quoting and booking creation."""

    session: AsyncSession

    async def get_available_slots(
        self, staff_id: str, booking_date: date, service_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Call the database availability function.

        Enriches the raw ``(slot_start, slot_end)`` rows with three extra
        fields so the frontend ``TimeSlotPicker`` can render without any
        client-side transformation:

        * ``id``         — stable key derived from the formatted start time
        * ``time``       — same human-readable label (e.g. "09:00 AM")
        * ``barberName`` — the staff member's display name
        """

        if not await self.staff_offers_services(staff_id, service_ids):
            return []

        duration = await self.get_service_duration_sum(staff_id, service_ids)
        result = await self.session.execute(
            text(
                """
                with staff_info as (
                  select st.name as barber_name, sl.timezone
                  from staff st
                  join salons sl on sl.id = st.salon_id
                  where st.id = :staff_id
                  limit 1
                )
                select
                  g.slot_start,
                  g.slot_end,
                  to_char(
                    g.slot_start at time zone coalesce(si.timezone, 'UTC'),
                    'HH12:MI AM'
                  ) as id,
                  to_char(
                    g.slot_start at time zone coalesce(si.timezone, 'UTC'),
                    'HH12:MI AM'
                  ) as time,
                  si.barber_name as "barberName"
                from get_available_slots(:staff_id, :booking_date, :duration_minutes) g
                cross join staff_info si
                """
            ),
            {"staff_id": staff_id, "booking_date": booking_date, "duration_minutes": duration},
        )
        return [dict(row) for row in result.mappings().all()]

    async def create_booking(self, values: dict[str, Any]) -> dict[str, Any]:
        """Call the database booking creation function and return the created booking."""

        try:
            key = values.get("_idempotency_key")
            scope = values.get("_idempotency_scope", "booking:create")
            try:
                replay = await self.begin_booking_operation(values.get("actor_id", ""), scope, key, values)
            except IdempotencyKeyReuseError as exc:
                raise BookingIdempotencyKeyReusedError(
                    "Idempotency-Key was already used for a different booking request"
                ) from exc
            if replay is not None:
                return {**replay, "_idempotency_replay": True}
            await self.session.execute(
                text("select set_config('app.payment_preference', :preference, true)"),
                {"preference": values.get("payment_preference") or "pay_at_salon"},
            )
            await self.session.execute(
                text("select set_config('app.booking_checkout_policy_version', :policy, true)"),
                {"policy": settings.booking_checkout_policy_version},
            )
            service_ids_json = json.dumps(values["service_ids"])
            result = await self.session.execute(
                text(
                    """
                    select create_booking(
                      :salon_id,
                      :staff_id,
                      array(
                        select value::uuid
                        from jsonb_array_elements_text(cast(:service_ids_json as jsonb)) value
                      ),
                      :start_datetime,
                      :customer_name, :customer_phone, cast(:source as booking_source), :notes
                    ) as booking_id
                    """
                ),
                {**values, "service_ids_json": service_ids_json},
            )
            booking_id = result.scalar_one()
            if settings.booking_checkout_policy_version != "customer_processing_v1":
                stored = await self.session.scalar(
                    text("select checkout_policy_version from bookings where id=:id"), {"id": booking_id},
                )
                if stored != settings.booking_checkout_policy_version:
                    from app.core.exceptions import ServiceUnavailableError
                    raise ServiceUnavailableError("Booking policy migration is not ready")
            if values.get("payment_preference") is not None:
                # The deposit is derived here, in SQL, from the price create_booking
                # computed. Python never recomputes or supplies an amount.
                await self.session.execute(
                    text(
                        """
                        update bookings
                        set payment_preference = cast(:payment_preference as text),
                            currency = :currency,
                            deposit_amount = case
                              when cast(:payment_preference as text) = 'pay_advance'
                                then least(total_price, greatest(
                                  round(total_price * cast(:advance_percent as numeric) / 100, 2),
                                  0.01))
                              when cast(:payment_preference as text) = 'pay_full'
                                then total_price
                              else null
                            end
                        where id = :booking_id
                        """
                    ),
                    {
                        "booking_id": booking_id,
                        "payment_preference": values["payment_preference"],
                        "currency": settings.payment_currency,
                        "advance_percent": settings.payment_advance_percent,
                    },
                )
            booking = await self.get_booking(str(booking_id), values.get("actor_id"))
            if booking is None:
                raise NotFoundError("Booking not found")
            await self.finish_booking_operation(values.get("actor_id", ""), scope, key, booking, 201)
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            if isinstance(exc, AppError) or not _is_business_error(exc):
                # Outages, timeouts and unexpected errors surface as 500, never as a 409.
                raise
            mapped = _error_for_message(str(exc), _CREATE_BOOKING_ERROR_RULES)
            if mapped is not None:
                raise mapped from exc
            raise ConflictError("Booking could not be created") from exc

        return booking

    async def begin_booking_operation(self, actor_id: str, scope: str, key: str | None, values: dict) -> dict | None:
        if key is None:
            return None
        from app.core.exceptions import IdempotencyKeyRequiredError
        from app.infrastructure.db.repositories.payment_repository import PaymentRepository
        if not 8 <= len(key) <= 200:
            raise IdempotencyKeyRequiredError("Idempotency-Key must be 8-200 characters")
        fingerprint = _request_fingerprint(values)
        return await PaymentRepository(self.session).begin_idempotent(actor_id, scope, key, fingerprint, 86400)

    async def finish_booking_operation(self, actor_id: str, scope: str, key: str | None, booking: dict, code: int = 200) -> None:
        if key is not None:
            from app.infrastructure.db.repositories.payment_repository import PaymentRepository
            await PaymentRepository(self.session).finish_idempotent(actor_id, scope, key, code, booking)

    async def quote_services(self, salon_id: str, staff_id: str, service_ids: list[str]) -> Any:
        result = await self.session.execute(text("""
            select sum(coalesce(ss.price_override, s.price)) as amount, count(*) as n,
                   sum(coalesce(ss.duration_minutes, s.duration_minutes)) as duration
            from services s join staff_services ss on ss.service_id = s.id and ss.staff_id = :staff
            join staff st on st.id = ss.staff_id
            where s.salon_id = :salon and st.salon_id = :salon and st.is_active
              and s.is_active and ss.is_active and s.id in (
                select value::uuid from jsonb_array_elements_text(cast(:ids as jsonb)) value)
        """), {"salon": salon_id, "staff": staff_id, "ids": json.dumps(service_ids)})
        row = result.mappings().one()
        if row["n"] != len(service_ids) or len(set(service_ids)) != len(service_ids):
            raise ValidationError("Selected services are not available from this staff member")
        return dict(row)

    async def checkout_salon(self, salon_id: str) -> dict:
        result = await self.session.execute(text("""
            select id, timezone, accepting_bookings from salons
            where id=:id and public.salon_booking_eligible(id)
        """), {"id":salon_id})
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        return dict(row)

    async def quoted_slot_available(self, staff_id, day, duration, start) -> bool:
        result = await self.session.execute(text("""
            select exists(select 1 from get_available_slots(:staff,:day,:duration)
                          where slot_start=:start)
        """), {"staff":staff_id,"day":day,"duration":int(duration),"start":start})
        return result.scalar_one()
