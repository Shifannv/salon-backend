"""Owner holidays, services, staff and staff-service links."""

import json
import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


class OwnerCatalogMixin:
    """Owner holidays, services, staff and staff-service links."""

    session: AsyncSession

    async def list_holidays(self, actor_id: str) -> list[dict[str, Any]]:
        """List owner salon holidays."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select id, salon_id, holiday_date, title, is_recurring, created_at, updated_at
                from salon_holidays
                where salon_id = :salon_id and is_active
                order by holiday_date
                """
            ),
            {"salon_id": salon["id"]},
        )
        return [dict(row) for row in result.mappings().all()]

    async def create_holiday(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Create an owner salon holiday."""

        salon = await self.get_owner_salon(actor_id)
        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtextextended(:salon_id, 0))"),
            {"salon_id": str(salon["id"])},
        )
        affected = await self._closure_affected_bookings(
            str(salon["id"]),
            {"kind": "holiday", "holiday_date": values["holiday_date"]},
            lock=True,
        )
        if affected:
            raise ConflictError("Holiday affects active bookings; preview the closure")
        result = await self.session.execute(
            text(
                """
                insert into salon_holidays (salon_id, holiday_date, title, is_recurring)
                values (:salon_id, :holiday_date, :title, :is_recurring)
                returning id, salon_id, holiday_date, title, is_recurring, created_at, updated_at
                """
            ),
            {
                "salon_id": salon["id"],
                "holiday_date": values["holiday_date"],
                "title": values.get("title"),
                "is_recurring": values.get("is_recurring", False),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def delete_holiday(self, actor_id: str, holiday_id: str) -> None:
        """Soft-delete an owner salon holiday."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                update salon_holidays
                set is_active = false
                where id = :holiday_id
                  and salon_id = :salon_id
                  and is_active
                returning id
                """
            ),
            {"holiday_id": holiday_id, "salon_id": salon["id"]},
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError("Holiday not found")
        await self.session.commit()

    async def list_owner_services(self, actor_id: str) -> list[dict[str, Any]]:
        """List services for the owner salon, including category and subcategory names."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select sv.id, sv.salon_id, sv.subcategory_id, sv.name,
                       sv.duration_minutes, sv.price, sv.is_active,
                       to_jsonb(sv)->>'menu_category_id' as menu_category_id,
                       case when to_jsonb(sv) ? 'selection_group' then to_jsonb(sv)->>'selection_group' else '__category__' end as selection_group,
                       sv.created_at, sv.updated_at,
                       coalesce(sv.category_name, sv.subcategory_name, ss.name, sc.name) as category_name,
                       coalesce(sv.subcategory_name, ss.name) as subcategory_name, sv.photo_url
                from services sv
                left join service_subcategories ss on ss.id = sv.subcategory_id
                left join service_categories sc on sc.id = ss.category_id
                where sv.salon_id = :salon_id
                order by sv.is_active desc, sc.sort_order, ss.sort_order, sv.name
                """
            ),
            {"salon_id": salon["id"]},
        )
        return [self._service_response(row) for row in result.mappings().all()]

    async def create_owner_service(self, actor_id: str, values: dict[str, Any], *, commit: bool = True) -> dict[str, Any]:
        """Create a salon service and return it with category/subcategory names."""

        salon = await self.get_owner_salon(actor_id)
        values = self._service_write_values(values)
        for field in ("category_name", "subcategory_name", "photo_url"):
            values.setdefault(field, None)
        subcategory_id = values.get("subcategory_id") or await self._default_service_subcategory_id()
        result = await self.session.execute(
            text(
                """
                insert into services (salon_id, subcategory_id, name,
                                      duration_minutes, price, is_active,
                                      category_name, subcategory_name, photo_url)
                values (:salon_id, :subcategory_id, :name,
                        :duration_minutes, :price, :is_active,
                        :category_name, :subcategory_name, :photo_url)
                returning id
                """
            ),
            {
                **values,
                "salon_id": salon["id"],
                "subcategory_id": subcategory_id,
                "is_active": values.get("is_active", True),
            },
        )
        service_id = str(result.scalar_one())
        if "selection_group" in values and values["selection_group"] != "__category__":
            await self.session.execute(text("update services set selection_group=:group where id=:id"),
                {"group": values["selection_group"], "id": service_id})
        if commit:
            await self.session.commit()
        return await self._get_service_with_categories(service_id)

    async def create_owner_services(self, actor_id: str, items: list[dict]) -> list[dict]:
        try:
            salon = await self.get_owner_salon(actor_id)
            await self.session.execute(text("select pg_advisory_xact_lock(hashtextextended(:id,0))"), {"id":str(salon["id"])})
            names = [item["name"].strip().casefold() for item in items]
            if len(names) != len(set(names)):
                raise ValidationError("Use a different name for each service")
            rows = [await self.create_owner_service(actor_id, item, commit=False) for item in items]
            await self.session.commit()
            return rows
        except Exception:
            await self.session.rollback()
            raise

    @staticmethod
    def _service_response(row: Any) -> dict[str, Any]:
        """Normalize DB UUID values for Pydantic v2 string response fields."""

        service = dict(row)
        service["id"] = str(service["id"])
        service["salon_id"] = str(service["salon_id"])
        service["subcategory_id"] = str(service["subcategory_id"])
        return service

    async def _get_service_with_categories(self, service_id: str) -> dict[str, Any]:
        """Re-fetch a service row joined with category and subcategory names.

        Used after INSERT/UPDATE where RETURNING cannot join other tables.
        """

        result = await self.session.execute(
            text(
                """
                select sv.id, sv.salon_id, sv.subcategory_id, sv.name,
                       sv.duration_minutes, sv.price, sv.is_active,
                       to_jsonb(sv)->>'menu_category_id' as menu_category_id,
                       case when to_jsonb(sv) ? 'selection_group' then to_jsonb(sv)->>'selection_group' else '__category__' end as selection_group,
                       sv.created_at, sv.updated_at,
                       coalesce(sv.category_name, sv.subcategory_name, ss.name, sc.name) as category_name,
                       coalesce(sv.subcategory_name, ss.name) as subcategory_name, sv.photo_url
                from services sv
                left join service_subcategories ss on ss.id = sv.subcategory_id
                left join service_categories sc on sc.id = ss.category_id
                where sv.id = :service_id
                """
            ),
            {"service_id": service_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Service not found")
        return self._service_response(row)

    async def _default_service_subcategory_id(self) -> str:
        """Return a general service subcategory for owner-created services."""

        category = await self.session.execute(
            text(
                """
                insert into service_categories (name, slug, description, sort_order, is_active)
                values ('General', 'general', 'Default category for owner-created services', 0, true)
                on conflict (slug) do update set is_active = true
                returning id
                """
            )
        )
        category_id = category.scalar_one()
        subcategory = await self.session.execute(
            text(
                """
                insert into service_subcategories (category_id, name, slug, description, sort_order, is_active)
                values (:category_id, 'General', 'general', 'Default subcategory for owner-created services', 0, true)
                on conflict (category_id, slug) do update set is_active = true
                returning id
                """
            ),
            {"category_id": category_id},
        )
        return str(subcategory.scalar_one())

    @staticmethod
    def _service_write_values(values: dict[str, Any]) -> dict[str, Any]:
        writable = {
            "subcategory_id", "name", "duration_minutes", "price",
            "is_active", "category_name", "subcategory_name", "photo_url", "selection_group",
        }
        if values.keys() - writable:
            raise ValidationError("Unsupported service fields")
        return {key: value for key, value in values.items() if key in writable}

    async def update_owner_service(
        self, actor_id: str, service_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a salon service and return it with category/subcategory names."""

        salon = await self.get_owner_salon(actor_id)
        allowed = self._service_write_values(values)
        if any(value is None for key, value in allowed.items()
               if key not in {"category_name", "subcategory_name", "photo_url", "selection_group"}):
            raise ValidationError("Required service fields cannot be null")
        if not allowed:
            raise ValidationError("No service fields provided")
        assignments = ", ".join(f"{key} = :{key}" for key in allowed)
        result = await self.session.execute(
            text(
                f"""
                update services
                set {assignments}
                where id = :service_id and salon_id = :salon_id
                returning id
                """
            ),
            {**allowed, "service_id": service_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Service not found")
        await self.session.commit()
        return await self._get_service_with_categories(str(row["id"]))

    async def deactivate_owner_service(self, actor_id: str, service_id: str) -> dict[str, Any]:
        """Soft-delete a salon service."""

        return await self.update_owner_service(actor_id, service_id, {"is_active": False})

    async def list_owner_staff(self, actor_id: str) -> list[dict[str, Any]]:
        """List staff for the owner salon."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select id, salon_id, profile_id, name, photo_url, specialization, experience,
                       working_hours, is_active, created_at, updated_at,
                       coalesce((select jsonb_agg(distinct l.name) from staff_service_languages ssl
                         join staff_services ss on ss.id=ssl.staff_service_id join languages l on l.code=ssl.language_code
                         join services sv on sv.id=ss.service_id where ss.staff_id=staff.id and ss.is_active and sv.is_active),'[]'::jsonb) as languages
                from staff
                where salon_id = :salon_id
                order by is_active desc, name
                """
            ),
            {"salon_id": salon["id"]},
        )
        return [self._staff_response(row) for row in result.mappings().all()]

    async def _assert_linkable_staff_profile(self, profile_id: str, salon_id: str) -> None:
        """Allow a staff row to point only at a staff login that no other salon already uses.

        Linking decides which workspace that login opens, so an owner must not be able to
        attach a customer, another owner or any account they merely know the id of.
        """

        refusal = ValidationError("That account cannot be linked as staff")
        try:
            uuid.UUID(str(profile_id))
        except ValueError:
            raise refusal from None
        result = await self.session.execute(
            text(
                """
                select p.role::text as role,
                       exists (select 1 from staff st
                               where st.profile_id = p.id and st.is_active
                                 and st.salon_id <> :salon_id) as used_elsewhere
                from profiles p
                where p.id = cast(:profile_id as uuid)
                """
            ),
            {"profile_id": str(profile_id), "salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        if row is None or row["role"] != "staff" or row["used_elsewhere"]:
            raise refusal

    async def create_owner_staff(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Create a staff member."""

        salon = await self.get_owner_salon(actor_id)
        if values.get("profile_id"):
            await self._assert_linkable_staff_profile(values["profile_id"], salon["id"])
        payload = self._prepare_jsonb_values(values)
        for key in ("profile_id", "photo_url", "specialization", "experience", "working_hours"):
            payload.setdefault(key, None)
        result = await self.session.execute(
            text(
                """
                insert into staff (
                  salon_id, profile_id, name, photo_url, specialization, experience, working_hours
                )
                values (
                  :salon_id, :profile_id, :name, :photo_url, :specialization, :experience,
                  cast(:working_hours as jsonb)
                )
                returning id, salon_id, profile_id, name, photo_url, specialization, experience,
                          working_hours, is_active, created_at, updated_at
                """
            ),
            {**payload, "salon_id": salon["id"]},
        )
        await self.session.commit()
        return self._staff_response(result.mappings().one())

    @staticmethod
    def _staff_response(row: Any) -> dict[str, Any]:
        """Normalize DB UUID values for Pydantic v2 string response fields."""

        staff = dict(row)
        staff["id"] = str(staff["id"])
        staff["salon_id"] = str(staff["salon_id"])
        if staff["profile_id"] is not None:
            staff["profile_id"] = str(staff["profile_id"])
        return staff

    async def update_owner_staff(
        self, actor_id: str, staff_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a staff member."""

        salon = await self.get_owner_salon(actor_id)
        allowed = self._prepare_jsonb_values(
            {key: value for key, value in values.items() if value is not None}
        )
        if not allowed:
            raise ValidationError("No staff fields provided")
        if allowed.get("profile_id"):
            await self._assert_linkable_staff_profile(allowed["profile_id"], salon["id"])
        assignments = ", ".join(self._sql_assignment(key) for key in allowed)
        result = await self.session.execute(
            text(
                f"""
                update staff
                set {assignments}
                where id = :staff_id and salon_id = :salon_id
                returning id, salon_id, profile_id, name, photo_url, specialization, experience,
                          working_hours, is_active, created_at, updated_at
                """
            ),
            {**allowed, "staff_id": staff_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Staff member not found")
        await self.session.commit()
        return self._staff_response(row)

    async def deactivate_owner_staff(self, actor_id: str, staff_id: str) -> dict[str, Any]:
        """Soft-delete a staff member."""

        return await self.update_owner_staff(actor_id, staff_id, {"is_active": False})

    async def assign_staff_service(
        self, actor_id: str, staff_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Assign a service to staff with optional overrides."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                insert into staff_services (
                  staff_id, service_id, duration_minutes, price_override, specialization, is_active
                )
                select :staff_id, :service_id, :duration_minutes, :price_override,
                       :specialization, true
                where exists (
                  select 1 from staff st
                  join services sv on sv.salon_id = st.salon_id
                  where st.id = :staff_id and sv.id = :service_id and st.salon_id = :salon_id
                )
                on conflict (staff_id, service_id) do update
                  set duration_minutes = excluded.duration_minutes,
                      price_override = excluded.price_override,
                      specialization = excluded.specialization,
                      is_active = true
                returning id, staff_id, service_id, duration_minutes, price_override,
                          specialization, is_active, created_at, updated_at
                """
            ),
            {**values, "staff_id": staff_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Staff member or service not found")
        await self.session.commit()
        return self._staff_service_response(row)

    @staticmethod
    def _staff_service_response(row: Any) -> dict[str, Any]:
        """Normalize DB UUID values for Pydantic v2 string response fields."""

        service = dict(row)
        service["id"] = str(service["id"])
        service["staff_id"] = str(service["staff_id"])
        service["service_id"] = str(service["service_id"])
        return service

    async def list_staff_services(self, actor_id: str, staff_id: str) -> list[dict[str, Any]]:
        """List service assignments for a staff member."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select ss.id, ss.staff_id, ss.service_id, ss.duration_minutes,
                       ss.price_override, ss.specialization, ss.is_active,
                       ss.created_at, ss.updated_at
                from staff_services ss
                join staff st on st.id = ss.staff_id
                join services sv on sv.id = ss.service_id and sv.salon_id = st.salon_id
                where ss.staff_id = :staff_id
                  and st.salon_id = :salon_id
                order by ss.is_active desc, sv.name
                """
            ),
            {"staff_id": staff_id, "salon_id": salon["id"]},
        )
        return [self._staff_service_response(row) for row in result.mappings().all()]

    async def get_service_duration_sum(self, staff_id: str, service_ids: Iterable[str]) -> int:
        """Return the effective duration for a service list and staff member."""

        ids = list(service_ids)
        if not ids:
            raise ValidationError("At least one service is required")
        result = await self.session.execute(
            text(
                """
                select sum(effective_duration(:staff_id, sid::uuid)) as duration
                from jsonb_array_elements_text(cast(:service_ids_json as jsonb)) sid
                """
            ),
            {"staff_id": staff_id, "service_ids_json": json.dumps(ids)},
        )
        duration = result.scalar_one_or_none()
        if duration is None:
            raise ValidationError("No valid services selected")
        return int(duration)

    async def staff_offers_services(self, staff_id: str, service_ids: Iterable[str]) -> bool:
        """Return whether a staff member actively offers every requested service."""

        ids = list(service_ids)
        if not ids:
            return False
        result = await self.session.execute(
            text(
                """
                select count(distinct ss.service_id) = :service_count
                from staff_services ss
                join staff st on st.id = ss.staff_id
                join services sv on sv.id = ss.service_id
                where ss.staff_id = :staff_id
                  and ss.service_id in (
                    select value::uuid
                    from jsonb_array_elements_text(cast(:service_ids_json as jsonb)) value
                  )
                  and ss.is_active
                  and st.is_active
                  and sv.is_active
                  and sv.salon_id = st.salon_id
                """
            ),
            {
                "staff_id": staff_id,
                "service_ids_json": json.dumps(ids),
                "service_count": len(set(ids)),
            },
        )
        return bool(result.scalar_one())

    async def get_staff_capabilities(self, actor_id: str, staff_id: str) -> dict:
        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(text("""
            select coalesce((select jsonb_agg(ss.service_id::text order by ss.service_id) from staff_services ss join services sv on sv.id=ss.service_id where ss.staff_id=st.id and ss.is_active and sv.is_active),'[]'::jsonb) as service_ids,
              coalesce((select jsonb_agg(distinct l.name) from staff_service_languages ssl
                join staff_services ss on ss.id=ssl.staff_service_id join languages l on l.code=ssl.language_code
                where ss.staff_id=st.id and ss.is_active),'[]'::jsonb) as languages
            from staff st where st.id=:staff and st.salon_id=:salon
        """), {"staff":staff_id,"salon":salon["id"]})
        row=result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Staff member not found")
        return dict(row)

    async def set_staff_capabilities(self, actor_id: str, staff_id: str, values: dict) -> dict:
        import json
        try:
            salon = await self.get_owner_salon(actor_id)
            await self.session.execute(text("select pg_advisory_xact_lock(hashtextextended(:salon,0))"), {"salon":str(salon["id"])})
            member = await self.session.scalar(text("select id from staff where id=:staff and salon_id=:salon for update"), {"staff":staff_id,"salon":salon["id"]})
            if member is None:
                raise NotFoundError("Staff member not found")
            ids=list(dict.fromkeys(values["service_ids"]))
            names=list(dict.fromkeys(name.strip().casefold() for name in values["languages"]))
            params={"staff":staff_id,"salon":salon["id"],"ids":json.dumps(ids),"names":json.dumps(names)}
            count=await self.session.scalar(text("""select count(*) from services where salon_id=:salon and is_active
                and id in(select value::uuid from jsonb_array_elements_text(cast(:ids as jsonb)))"""),params)
            language_count=await self.session.scalar(text("""select count(*) from languages
                where lower(name) in(select value from jsonb_array_elements_text(cast(:names as jsonb)))"""),params)
            if count!=len(ids) or language_count!=len(names):
                raise ValidationError("Choose services from this salon and supported languages")
            await self.session.execute(text("""update staff_services set is_active=false where staff_id=:staff
                and service_id not in(select value::uuid from jsonb_array_elements_text(cast(:ids as jsonb)))"""),params)
            await self.session.execute(text("""insert into staff_services(staff_id,service_id)
                select :staff,value::uuid from jsonb_array_elements_text(cast(:ids as jsonb))
                on conflict(staff_id,service_id) do update set is_active=true"""),params)
            await self.session.execute(text("""delete from staff_service_languages where staff_service_id in
                (select id from staff_services where staff_id=:staff and is_active)"""),params)
            await self.session.execute(text("""insert into staff_service_languages(staff_service_id,language_code)
                select ss.id,l.code from staff_services ss cross join languages l where ss.staff_id=:staff and ss.is_active
                and lower(l.name) in(select value from jsonb_array_elements_text(cast(:names as jsonb)))
                on conflict do nothing"""),params)
            await self.session.commit()
            return await self.get_staff_capabilities(actor_id,staff_id)
        except Exception:
            await self.session.rollback()
            raise
