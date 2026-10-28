"""Staff service languages and blocked slots."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


class LanguagesSlotsMixin:
    """Staff service languages and blocked slots."""

    session: AsyncSession

    async def list_available_languages(self) -> list[dict[str, Any]]:
        """Return all languages from the languages reference table."""

        result = await self.session.execute(
            text("select code, name from languages order by name")
        )
        return [dict(row) for row in result.mappings().all()]

    async def list_staff_service_languages(
        self, actor_id: str, staff_id: str, staff_service_id: str
    ) -> list[dict[str, Any]]:
        """List languages for a staff service assignment."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select ssl.language_code as code, l.name
                from staff_service_languages ssl
                join languages l on l.code = ssl.language_code
                join staff_services ss on ss.id = ssl.staff_service_id
                join staff st on st.id = ss.staff_id
                where ssl.staff_service_id = :staff_service_id
                  and ss.staff_id = :staff_id
                  and st.salon_id = :salon_id
                order by l.name
                """
            ),
            {
                "staff_service_id": staff_service_id,
                "staff_id": staff_id,
                "salon_id": salon["id"],
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def set_staff_service_languages(
        self, actor_id: str, staff_id: str, staff_service_id: str, language_codes: list[str]
    ) -> list[dict[str, Any]]:
        """Replace language assignments for a staff service (idempotent)."""

        salon = await self.get_owner_salon(actor_id)
        # Verify ownership
        check = await self.session.execute(
            text(
                """
                select ss.id from staff_services ss
                join staff st on st.id = ss.staff_id
                where ss.id = :staff_service_id
                  and ss.staff_id = :staff_id
                  and st.salon_id = :salon_id
                """
            ),
            {
                "staff_service_id": staff_service_id,
                "staff_id": staff_id,
                "salon_id": salon["id"],
            },
        )
        if check.one_or_none() is None:
            raise NotFoundError("Staff service assignment not found")
        # Replace all
        await self.session.execute(
            text(
                "delete from staff_service_languages where staff_service_id = :id"
            ),
            {"id": staff_service_id},
        )
        for code in language_codes:
            await self.session.execute(
                text(
                    """
                    insert into staff_service_languages (staff_service_id, language_code)
                    values (:staff_service_id, :code)
                    on conflict do nothing
                    """
                ),
                {"staff_service_id": staff_service_id, "code": code},
            )
        await self.session.commit()
        return await self.list_staff_service_languages(actor_id, staff_id, staff_service_id)

    # ------------------------------------------------------------------
    # Blocked slots
    # ------------------------------------------------------------------

    async def list_blocked_slots(self, actor_id: str) -> list[dict[str, Any]]:
        """List blocked slots for the actor's salon."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select id, staff_id, salon_id, start_datetime, end_datetime,
                       block_type, reason, is_full_day, is_recurring,
                       recurrence_rule, recurrence_end, created_at, updated_at
                from blocked_slots
                where salon_id = :salon_id
                order by start_datetime desc
                limit 200
                """
            ),
            {"salon_id": salon["id"]},
        )
        return [dict(row) for row in result.mappings().all()]

    async def create_blocked_slot(
        self, actor_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a blocked slot (staff-scoped or salon-wide)."""

        if values.get("block_type") == "leave" and not (
            values.get("reason") or ""
        ).strip():
            raise ValidationError("A reason is required for salon leave")
        salon = await self.get_owner_salon(actor_id)
        # If staff_id provided, verify it belongs to this salon
        if values.get("staff_id"):
            check = await self.session.execute(
                text(
                    "select id from staff where id = :staff_id and salon_id = :salon_id"
                ),
                {"staff_id": values["staff_id"], "salon_id": salon["id"]},
            )
            if check.one_or_none() is None:
                raise NotFoundError("Staff member not found in this salon")

        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtextextended(:salon_id, 0))"),
            {"salon_id": str(salon["id"])},
        )
        affected = await self._closure_affected_bookings(
            str(salon["id"]),
            {
                "kind": "leave",
                "staff_id": values.get("staff_id"),
                "start_datetime": values["start_datetime"],
                "end_datetime": values["end_datetime"],
            },
            lock=True,
        )
        if affected:
            raise ConflictError("Blocked time affects active bookings; preview the closure")

        result = await self.session.execute(
            text(
                """
                insert into blocked_slots (
                  staff_id, salon_id, start_datetime, end_datetime,
                  block_type, reason, is_full_day, is_recurring,
                  recurrence_rule, recurrence_end
                ) values (
                  :staff_id, :salon_id, :start_datetime, :end_datetime,
                  :block_type, :reason, :is_full_day, :is_recurring,
                  :recurrence_rule, :recurrence_end
                )
                returning id, staff_id, salon_id, start_datetime, end_datetime,
                          block_type, reason, is_full_day, is_recurring,
                          recurrence_rule, recurrence_end, created_at, updated_at
                """
            ),
            {
                "staff_id": values.get("staff_id"),
                "salon_id": salon["id"],
                "start_datetime": values["start_datetime"],
                "end_datetime": values["end_datetime"],
                "block_type": values.get("block_type", "other"),
                "reason": values.get("reason"),
                "is_full_day": values.get("is_full_day", False),
                "is_recurring": values.get("is_recurring", False),
                "recurrence_rule": values.get("recurrence_rule"),
                "recurrence_end": values.get("recurrence_end"),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def delete_blocked_slot(self, actor_id: str, slot_id: str) -> None:
        """Hard-delete a blocked slot (blocked slots have no is_active column)."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                delete from blocked_slots
                where id = :slot_id and salon_id = :salon_id
                returning id
                """
            ),
            {"slot_id": slot_id, "salon_id": salon["id"]},
        )
        if result.one_or_none() is None:
            raise NotFoundError("Blocked slot not found")
        await self.session.commit()

    # ------------------------------------------------------------------
    # Walk-in QR
    # ------------------------------------------------------------------
