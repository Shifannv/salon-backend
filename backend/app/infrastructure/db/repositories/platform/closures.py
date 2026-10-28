"""Salon closures."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
)


class ClosuresMixin:
    """Salon closures."""

    session: AsyncSession

    async def _closure_affected_bookings(
        self,
        salon_id: str,
        values: dict[str, Any],
        *,
        lock: bool,
    ) -> list[dict[str, Any]]:
        if values["kind"] == "holiday":
            predicate = """
                tstzrange(b.start_datetime, b.end_datetime, '[)')
                  && tstzrange(
                    (cast(:holiday_date as date) + time '00:00') at time zone s.timezone,
                    (cast(:holiday_date as date) + interval '1 day') at time zone s.timezone,
                    '[)'
                  )
            """
            params = {
                "salon_id": salon_id,
                "holiday_date": values["holiday_date"],
            }
        else:
            predicate = """
                tstzrange(b.start_datetime, b.end_datetime, '[)')
                  && tstzrange(:start_datetime, :end_datetime, '[)')
                and (cast(:staff_id as uuid) is null or b.staff_id = cast(:staff_id as uuid))
            """
            params = {
                "salon_id": salon_id,
                "start_datetime": values["start_datetime"],
                "end_datetime": values["end_datetime"],
                "staff_id": values.get("staff_id"),
            }
        lock_sql = "for update of b" if lock else ""
        result = await self.session.execute(
            text(
                f"""
                select b.id as booking_id, b.customer_id, b.customer_name,
                       b.staff_id, b.start_datetime, b.end_datetime, b.status,
                       coalesce(
                         array(
                           select bs.service_name from booking_services bs
                           where bs.booking_id = b.id and coalesce((to_jsonb(bs)->>'is_active')::boolean, true) order by bs.service_name
                         ), array[]::text[]
                       ) as service_names
                from bookings b
                join salons s on s.id = b.salon_id
                where b.salon_id = :salon_id
                  and b.status in ('pending', 'confirmed')
                  and {predicate}
                order by b.start_datetime, b.id
                {lock_sql}
                """
            ),
            params,
        )
        rows = []
        for row in result.mappings().all():
            item = dict(row)
            for key in ("booking_id", "customer_id", "staff_id"):
                if item.get(key) is not None:
                    item[key] = str(item[key])
            rows.append(item)
        return rows

    async def preview_closure(
        self, actor_id: str, values: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Preview exactly the active bookings overlapped by a closure."""

        salon = await self.get_owner_salon(actor_id)
        if values.get("staff_id"):
            staff = await self.session.execute(
                text(
                    "select id from staff where id = :staff_id and salon_id = :salon_id"
                ),
                {"staff_id": values["staff_id"], "salon_id": salon["id"]},
            )
            if staff.scalar_one_or_none() is None:
                raise NotFoundError("Staff member not found in this salon")
        return await self._closure_affected_bookings(
            str(salon["id"]), values, lock=False
        )

    async def apply_closure(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply a closure and cancel its exact confirmed impact set."""

        salon = await self.get_owner_salon(actor_id)
        salon_id = str(salon["id"])
        if values.get("staff_id"):
            staff = await self.session.execute(
                text(
                    "select id from staff where id = :staff_id and salon_id = :salon_id"
                ),
                {"staff_id": values["staff_id"], "salon_id": salon_id},
            )
            if staff.scalar_one_or_none() is None:
                raise NotFoundError("Staff member not found in this salon")

        # Booking inserts acquire the same lock in t_bookings_closure_guard.
        # This closes the preview/apply race without weakening create_booking.
        await self.session.execute(
            text(
                "select pg_advisory_xact_lock(hashtextextended(:salon_id, 0))"
            ),
            {"salon_id": salon_id},
        )
        affected = await self._closure_affected_bookings(
            salon_id, values, lock=True
        )
        actual_ids = {item["booking_id"] for item in affected}
        supplied_ids = values.get("affected_booking_ids", [])
        expected_ids = set(supplied_ids)
        if len(supplied_ids) != len(expected_ids) or actual_ids != expected_ids:
            raise ConflictError(
                "Affected bookings changed after preview; refresh and confirm again"
            )

        if values["kind"] == "holiday":
            created = await self.session.execute(
                text(
                    """
                    insert into salon_holidays (
                      salon_id, holiday_date, title, reason, is_recurring
                    ) values (
                      :salon_id, :holiday_date, :title, :reason, false
                    )
                    on conflict (salon_id, holiday_date) where is_active do nothing
                    returning id
                    """
                ),
                {
                    "salon_id": salon_id,
                    "holiday_date": values["holiday_date"],
                    "title": values.get("title") or values["reason"],
                    "reason": values["reason"],
                },
            )
        else:
            created = await self.session.execute(
                text(
                    """
                    insert into blocked_slots (
                      staff_id, salon_id, start_datetime, end_datetime,
                      block_type, reason, is_full_day, is_recurring
                    ) values (
                      :staff_id, :salon_id, :start_datetime, :end_datetime,
                      'leave', :reason, false, false
                    )
                    returning id
                    """
                ),
                {
                    "staff_id": values.get("staff_id"),
                    "salon_id": salon_id,
                    "start_datetime": values["start_datetime"],
                    "end_datetime": values["end_datetime"],
                    "reason": values["reason"],
                },
            )
        created_id = created.scalar_one_or_none()
        if created_id is None:
            raise ConflictError("An active holiday already exists for this date")
        closure_id = str(created_id)

        outbox_ids: list[str] = []
        if actual_ids:
            ids_json = json.dumps(sorted(actual_ids))
            await self.session.execute(
                text(
                    """
                    update bookings
                    set status = 'cancelled', cancellation_reason = :reason
                    where id in (
                      select value::uuid
                      from jsonb_array_elements_text(cast(:ids_json as jsonb)) value
                    )
                    """
                ),
                {"ids_json": ids_json, "reason": values["reason"]},
            )
            await self.session.execute(
                text(
                    """
                    update booking_action_requests
                    set status = 'resolved', decision = 'invalidated',
                        decision_reason = 'Booking cancelled by salon closure',
                        resolved_by = :actor_id, resolved_at = now()
                    where booking_id in (
                      select value::uuid
                      from jsonb_array_elements_text(cast(:ids_json as jsonb)) value
                    ) and status = 'pending'
                    """
                ),
                {"ids_json": ids_json, "actor_id": actor_id},
            )
            for booking in affected:
                booking["status"] = "cancelled"
                if booking["customer_id"]:
                    outbox_ids.append(
                        await self._insert_notification_outbox(
                            user_id=booking["customer_id"],
                            booking_id=booking["booking_id"],
                            notification_type="booking_cancelled_closure",
                            title="Appointment cancelled by salon",
                            body=(
                                f"The salon closed this time because: {values['reason']}. "
                                "Please book another available appointment."
                            ),
                        )
                    )

        await self.session.commit()
        return {
            "closure_kind": values["kind"],
            "closure_id": closure_id,
            "reason": values["reason"],
            "affected_count": len(affected),
            "affected_bookings": affected,
            "_outbox_ids": outbox_ids,
        }
