"""Raw SQL repository adapter for frontend-facing platform APIs."""

import json
from collections.abc import Iterable
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, SlotUnavailableError, ValidationError


class PlatformRepository:
    """Database adapter for customer and salon-owner use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _prepare_jsonb_values(self, values: dict[str, Any]) -> dict[str, Any]:
        """Serialize JSONB fields for raw SQL text statements."""

        prepared = dict(values)
        if "working_hours" in prepared and prepared["working_hours"] is not None:
            prepared["working_hours"] = json.dumps(prepared["working_hours"])
        return prepared

    def _sql_value_placeholder(self, key: str) -> str:
        """Return the SQL placeholder for a writable column."""

        if key == "working_hours":
            return f"cast(:{key} as jsonb)"
        return f":{key}"

    def _sql_assignment(self, key: str) -> str:
        """Return a safe assignment fragment for a writable column."""

        return f"{key} = {self._sql_value_placeholder(key)}"

    def _profile_response(self, row: Any) -> dict[str, Any]:
        """Normalize profile rows for Pydantic response schemas."""

        profile = dict(row)
        profile["id"] = str(profile["id"])
        return profile

    async def update_profile(self, profile_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Update the actor's profile.

        ``values`` contains only keys the caller explicitly set (``exclude_unset`` in the
        Pydantic schema).  An explicit ``null`` clears the corresponding nullable column
        (phone, full_name, avatar_url).  Omitted keys are not in the dict at all, so they
        are never touched.
        """

        # Empty dict → nothing was sent; return the current row unchanged.
        if not values:
            profile = await self.get_profile(profile_id)
            if profile is None:
                raise NotFoundError("Profile not found")
            return profile

        assignments = ", ".join(self._sql_assignment(key) for key in values)
        result = await self.session.execute(
            text(
                f"""
                update profiles
                set {assignments}
                where id = :profile_id
                returning id, role, full_name, email, phone, phone_verified, avatar_url, is_active
                """
            ),
            {**values, "profile_id": profile_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Profile not found")
        await self.session.commit()
        return self._profile_response(row)

    async def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        """Read a profile row."""

        result = await self.session.execute(
            text(
                """
                select id, role, full_name, email, phone, phone_verified, avatar_url, is_active
                from profiles
                where id = :profile_id
                """
            ),
            {"profile_id": profile_id},
        )
        row = result.mappings().one_or_none()
        return self._profile_response(row) if row else None

    async def list_salons(
        self,
        *,
        search: str | None,
        city: str | None,
        lat: float | None,
        lng: float | None,
        limit: int,
        offset: int,
        ids: list[str] | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """List public active completed salons.

        Services are NOT bundled. Callers that need service data should use
        the dedicated GET /salons/{salon_id}/services endpoint.

        ``category`` filters to salons that have at least one active, staff-assigned
        service whose ``service_categories.name`` matches the value (ILIKE wildcard).
        For example ``category="Hair Cutting"`` matches the "Hair Cutting" category row.
        Omit or pass ``None`` to return all categories.
        """

        normalized_ids: list[str] = []
        if ids is not None:
            for salon_id in ids:
                try:
                    normalized_ids.append(str(UUID(salon_id.strip())))
                except (AttributeError, TypeError, ValueError):
                    continue
            if not normalized_ids:
                return []
        params = {
            "search": f"%{search}%" if search else None,
            "city": city,
            "lat": lat,
            "lng": lng,
            "ids": normalized_ids,
            "limit": limit,
            "offset": offset,
            "category_pattern": f"%{category}%" if category else None,
        }
        ids_filter = "and s.id in :ids" if normalized_ids else ""
        statement = text(
            f"""
            select
              s.id, s.name, s.description, s.category, s.address, s.city,
              s.lat, s.lng, s.timezone, s.working_hours, s.approval_mode, s.profile_completed,
              s.is_active, img.url as image_url, min(sv.price) as starting_price,
              case
                when cast(:lat as double precision) is not null
                     and cast(:lng as double precision) is not null
                     and s.lat is not null and s.lng is not null
                then 6371 * acos(
                  least(1, greatest(-1,
                    cos(radians(cast(:lat as double precision))) * cos(radians(s.lat)) *
                    cos(radians(s.lng) - radians(cast(:lng as double precision))) +
                    sin(radians(cast(:lat as double precision))) * sin(radians(s.lat))
                  ))
                )
                else null
              end as distance_km
            from salons s
            left join lateral (
              select url
              from salon_images
              where salon_id = s.id
              order by is_main desc, sort_order asc, created_at asc
              limit 1
            ) img on true
            left join services sv on sv.salon_id = s.id
              and sv.is_active
              and exists (
                select 1
                from staff_services stsv
                join staff st on st.id = stsv.staff_id
                where stsv.service_id = sv.id
                  and stsv.is_active
                  and st.is_active
                  and st.salon_id = sv.salon_id
              )
            where s.is_active and s.profile_completed
              and (cast(:search as text) is null or s.name ilike cast(:search as text))
              and (cast(:city as text) is null or s.city = cast(:city as text))
              {ids_filter}
            group by s.id, img.url
            having (
              cast(:category_pattern as text) is null
              or exists (
                select 1
                from services sv2
                join service_subcategories ss2 on ss2.id = sv2.subcategory_id
                join service_categories sc2 on sc2.id = ss2.category_id
                where sv2.salon_id = s.id
                  and sv2.is_active
                  and ss2.is_active
                  and sc2.is_active
                  and sc2.name ilike cast(:category_pattern as text)
              )
            )
            order by distance_km nulls last, s.name
            limit cast(:limit as int) offset cast(:offset as int)
            """
        )
        if normalized_ids:
            statement = statement.bindparams(bindparam("ids", expanding=True))
        result = await self.session.execute(
            statement,
            params,
        )
        rows = result.mappings().all()
        return [{**dict(row), "id": str(row["id"])} for row in rows]

    async def get_public_salon(self, salon_id: str) -> dict[str, Any]:
        """Read public salon details (core fields + images only).

        Services and staff are NOT bundled here. Use the dedicated endpoints:
          - GET /salons/{salon_id}/services
          - GET /salons/{salon_id}/staff
        """

        result = await self.session.execute(
            text(
                """
                select id, name, description, category, address, city, lat, lng, timezone,
                       working_hours, approval_mode, slot_interval_minutes, profile_completed,
                       is_active
                from salons
                where id = :salon_id and is_active and profile_completed
                """
            ),
            {"salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        salon = dict(row)
        salon["id"] = str(salon["id"])
        salon["images"] = await self.list_salon_images(salon_id)
        return salon

    async def list_public_staff(self, salon_id: str) -> list[dict[str, Any]]:
        """List active staff for a public salon (customer-facing, trimmed fields)."""

        result = await self.session.execute(
            text(
                """
                select id, name, photo_url, specialization
                from staff
                where salon_id = :salon_id and is_active
                order by name
                """
            ),
            {"salon_id": salon_id},
        )
        rows = result.mappings().all()
        return [{**dict(row), "id": str(row["id"])} for row in rows]

    async def list_public_services(self, salon_id: str) -> list[dict[str, Any]]:
        """List public active services for a salon."""

        result = await self.session.execute(
            text(
                """
                select sv.id, sv.salon_id, sv.subcategory_id, sv.name, sv.description,
                       sv.duration_minutes, sv.price, sv.is_active,
                       sc.name as category_name, ss.name as subcategory_name
                from services sv
                join service_subcategories ss on ss.id = sv.subcategory_id
                join service_categories sc on sc.id = ss.category_id
                where sv.salon_id = :salon_id
                  and sv.is_active and ss.is_active and sc.is_active
                  and exists (
                    select 1
                    from staff_services stsv
                    join staff st on st.id = stsv.staff_id
                    where stsv.service_id = sv.id
                      and stsv.is_active
                      and st.is_active
                      and st.salon_id = sv.salon_id
                  )
                order by sc.sort_order, ss.sort_order, sv.name
                """
            ),
            {"salon_id": salon_id},
        )
        rows = result.mappings().all()
        return [
            {
                **dict(row),
                "id": str(row["id"]),
                "salon_id": str(row["salon_id"]),
                "subcategory_id": str(row["subcategory_id"]) if row.get("subcategory_id") else None,
            }
            for row in rows
        ]

    async def list_public_services_for_salons(self, salon_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        """List public active services grouped by salon for summary cards."""

        if not salon_ids:
            return {}
        result = await self.session.execute(
            text(
                """
                select sv.id, sv.salon_id, sv.subcategory_id, sv.name, sv.description,
                       sv.duration_minutes, sv.price, sv.is_active,
                       sc.name as category_name, ss.name as subcategory_name
                from services sv
                join service_subcategories ss on ss.id = sv.subcategory_id
                join service_categories sc on sc.id = ss.category_id
                where sv.salon_id in (
                    select value::uuid
                    from jsonb_array_elements_text(cast(:salon_ids_json as jsonb)) value
                )
                  and sv.is_active and ss.is_active and sc.is_active
                  and exists (
                    select 1
                    from staff_services stsv
                    join staff st on st.id = stsv.staff_id
                    where stsv.service_id = sv.id
                      and stsv.is_active
                      and st.is_active
                      and st.salon_id = sv.salon_id
                  )
                order by sv.salon_id, sc.sort_order, ss.sort_order, sv.name
                """
            ),
            {"salon_ids_json": json.dumps(salon_ids)},
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in result.mappings().all():
            service = {
                **dict(row),
                "id": str(row["id"]),
                "salon_id": str(row["salon_id"]),
                "subcategory_id": str(row["subcategory_id"]) if row.get("subcategory_id") else None,
            }
            grouped.setdefault(service["salon_id"], []).append(service)
        return grouped

    async def list_salon_images(self, salon_id: str) -> list[dict[str, Any]]:
        """List active images for a salon.

        Soft-deleted images (is_active = false) are excluded.
        """

        result = await self.session.execute(
            text(
                """
                select id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
                from salon_images
                where salon_id = :salon_id
                  and is_active = true
                order by is_main desc, sort_order asc, created_at asc
                """
            ),
            {"salon_id": salon_id},
        )
        rows = result.mappings().all()
        return [
            {
                **dict(row),
                "id": str(row["id"]),
                "salon_id": str(row["salon_id"]),
            }
            for row in rows
        ]

    async def delete_salon_image(self, actor_id: str, image_id: str) -> str | None:
        """Soft-delete a salon image (set is_active = false).

        Returns the ``url`` of the deleted row so the caller can clean up the
        corresponding R2 object, or ``None`` if the image was not found.
        """

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                update salon_images
                   set is_active = false
                 where id = :image_id
                   and salon_id = :salon_id
                   and is_active = true
                returning url
                """
            ),
            {"image_id": image_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        await self.session.commit()
        return str(row["url"])

    async def get_owner_salon(self, actor_id: str) -> dict[str, Any]:
        """Return the salon owned by an actor, auto-provisioning a blank one on first login.

        Owners are created via the Supabase ``handle_new_user`` trigger which only inserts
        into ``profiles``. A salon row does not exist until either an admin creates it or —
        for Google OAuth owners — this method creates it on the first owner-salon request.
        """

        row = await self._get_owner_salon_row(actor_id)
        if row is None:
            return await self.provision_owner_salon(actor_id)
        return await self._owner_salon_with_images(row)

    async def _lock_owner_salon(self, actor_id: str) -> None:
        """Serialize owner-salon creation for one actor within this API."""

        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtext(:actor_id))"),
            {"actor_id": actor_id},
        )

    async def _owner_salon_with_images(self, row: Any) -> dict[str, Any]:
        """Return an owner salon row in the shape expected by the owner app."""

        salon = dict(row)
        salon["id"] = str(salon["id"])
        salon["owner_id"] = str(salon["owner_id"])
        salon["images"] = await self.list_salon_images(salon["id"])
        return salon

    async def _get_owner_salon_row(self, actor_id: str):
        """Raw DB read — returns the mapping row or None, never raises."""

        result = await self.session.execute(
            text(
                """
                select id, owner_id, name, description, category, address, city, lat, lng,
                       timezone, working_hours, approval_mode, slot_interval_minutes,
                       qr_token, profile_completed, is_active, created_at, updated_at
                from salons
                where owner_id = :actor_id and is_active
                order by created_at asc
                limit 1
                """
            ),
            {"actor_id": actor_id},
        )
        return result.mappings().one_or_none()

    async def provision_owner_salon(self, actor_id: str) -> dict[str, Any]:
        """Create a blank salon for a new owner and return it.

        Idempotent for API traffic: an owner-scoped advisory lock makes concurrent
        first-login requests check for an existing active salon before inserting.
        """

        await self._lock_owner_salon(actor_id)
        existing = await self._get_owner_salon_row(actor_id)
        if existing is not None:
            return await self._owner_salon_with_images(existing)

        result = await self.session.execute(
            text(
                """
                insert into salons (owner_id, name, is_active, profile_completed)
                values (:actor_id, '', true, false)
                returning id, owner_id, name, description, category, address, city, lat, lng,
                          timezone, working_hours, approval_mode, slot_interval_minutes,
                          qr_token, profile_completed, is_active, created_at, updated_at
                """
            ),
            {"actor_id": actor_id},
        )
        await self.session.commit()
        return await self._owner_salon_with_images(result.mappings().one())

    async def update_owner_salon(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Update owner-editable salon fields."""

        salon = await self.get_owner_salon(actor_id)
        # _prepare_jsonb_values serialises working_hours so Postgres receives a JSON string
        # that can be cast to jsonb, not a raw Python dict which would raise ProgrammingError.
        allowed = self._prepare_jsonb_values(
            {key: value for key, value in values.items() if value is not None}
        )
        if not allowed:
            return salon

        # _sql_assignment emits `key = :key` for plain columns and
        # `key = cast(:key as jsonb)` for working_hours — same as complete_owner_salon.
        assignments = ", ".join(self._sql_assignment(key) for key in allowed)
        result = await self.session.execute(
            text(
                f"""
                update salons
                set {assignments}
                where id = :salon_id and owner_id = :actor_id and is_active
                returning id, owner_id, name, description, category, address, city, lat, lng,
                          timezone, working_hours, approval_mode, slot_interval_minutes,
                          qr_token, profile_completed, is_active, created_at, updated_at
                """
            ),
            {**allowed, "salon_id": salon["id"], "actor_id": actor_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        await self.session.commit()
        return await self._owner_salon_with_images(row)

    async def complete_owner_salon(
        self, actor_id: str, values: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create/update the owner's salon from onboarding data and publish it."""

        allowed = self._prepare_jsonb_values(dict(values or {}))
        payload = {**allowed, "profile_completed": True}

        await self._lock_owner_salon(actor_id)
        salon = await self._get_owner_salon_row(actor_id)
        if salon is None:
            if not payload.get("name"):
                raise ValidationError("Salon name is required to complete setup")
            fields = ["owner_id", *payload.keys()]
            params = {"owner_id": actor_id, **payload}
            columns = ", ".join(fields)
            placeholders = ", ".join(self._sql_value_placeholder(field) for field in fields)
            result = await self.session.execute(
                text(
                    f"""
                    insert into salons ({columns})
                    values ({placeholders})
                    returning id, owner_id, name, description, category, address, city, lat, lng,
                              timezone, working_hours, approval_mode, slot_interval_minutes,
                              qr_token, profile_completed, is_active, created_at, updated_at
                    """
                ),
                params,
            )
            await self.session.commit()
            return await self._owner_salon_with_images(result.mappings().one())

        assignments = ", ".join(self._sql_assignment(key) for key in payload)
        result = await self.session.execute(
            text(
                f"""
                update salons
                set {assignments}
                where id = :salon_id and owner_id = :actor_id and is_active
                returning id, owner_id, name, description, category, address, city, lat, lng,
                          timezone, working_hours, approval_mode, slot_interval_minutes,
                          qr_token, profile_completed, is_active, created_at, updated_at
                """
            ),
            {**payload, "salon_id": salon["id"], "actor_id": actor_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        await self.session.commit()
        return await self._owner_salon_with_images(row)

    async def create_salon_image(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Create an image for the owner's salon."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                insert into salon_images (salon_id, url, caption, is_main, sort_order)
                values (:salon_id, :url, :caption, :is_main, :sort_order)
                returning id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
                """
            ),
            {
                "salon_id": salon["id"],
                "url": values["url"],
                "caption": values.get("caption"),
                "is_main": values.get("is_main", False),
                "sort_order": values.get("sort_order", 0),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_salon_image(
        self, actor_id: str, image_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an owner salon image."""

        salon = await self.get_owner_salon(actor_id)
        allowed = {key: value for key, value in values.items() if value is not None}
        if not allowed:
            images = [img for img in await self.list_salon_images(salon["id"]) if str(img["id"]) == image_id]
            if not images:
                raise NotFoundError("Image not found")
            return images[0]
        assignments = ", ".join(f"{key} = :{key}" for key in allowed)
        result = await self.session.execute(
            text(
                f"""
                update salon_images
                set {assignments}
                where id = :image_id and salon_id = :salon_id
                returning id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
                """
            ),
            {**allowed, "image_id": image_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Image not found")
        await self.session.commit()
        return dict(row)

    async def list_holidays(self, actor_id: str) -> list[dict[str, Any]]:
        """List owner salon holidays."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select id, salon_id, holiday_date, title, is_recurring, created_at, updated_at
                from salon_holidays
                where salon_id = :salon_id
                order by holiday_date
                """
            ),
            {"salon_id": salon["id"]},
        )
        return [dict(row) for row in result.mappings().all()]

    async def create_holiday(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Create an owner salon holiday."""

        salon = await self.get_owner_salon(actor_id)
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

    async def list_owner_services(self, actor_id: str) -> list[dict[str, Any]]:
        """List services for the owner salon."""

        salon = await self.get_owner_salon(actor_id)
        result = await self.session.execute(
            text(
                """
                select id, salon_id, subcategory_id, name, description, duration_minutes,
                       price, is_active, created_at, updated_at
                from services
                where salon_id = :salon_id
                order by is_active desc, name
                """
            ),
            {"salon_id": salon["id"]},
        )
        return [self._service_response(row) for row in result.mappings().all()]

    async def create_owner_service(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Create a salon service."""

        salon = await self.get_owner_salon(actor_id)
        subcategory_id = values.get("subcategory_id") or await self._default_service_subcategory_id()
        result = await self.session.execute(
            text(
                """
                insert into services (salon_id, subcategory_id, name, description, duration_minutes, price, is_active)
                values (:salon_id, :subcategory_id, :name, :description, :duration_minutes, :price, :is_active)
                returning id, salon_id, subcategory_id, name, description, duration_minutes,
                          price, is_active, created_at, updated_at
                """
            ),
            {
                **values,
                "salon_id": salon["id"],
                "subcategory_id": subcategory_id,
                "is_active": values.get("is_active", True),
            },
        )
        await self.session.commit()
        return self._service_response(result.mappings().one())

    @staticmethod
    def _service_response(row: Any) -> dict[str, Any]:
        """Normalize DB UUID values for Pydantic v2 string response fields."""

        service = dict(row)
        service["id"] = str(service["id"])
        service["salon_id"] = str(service["salon_id"])
        service["subcategory_id"] = str(service["subcategory_id"])
        return service

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

    async def update_owner_service(
        self, actor_id: str, service_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a salon service."""

        salon = await self.get_owner_salon(actor_id)
        allowed = {key: value for key, value in values.items() if value is not None}
        if not allowed:
            raise ValidationError("No service fields provided")
        assignments = ", ".join(f"{key} = :{key}" for key in allowed)
        result = await self.session.execute(
            text(
                f"""
                update services
                set {assignments}
                where id = :service_id and salon_id = :salon_id
                returning id, salon_id, subcategory_id, name, description, duration_minutes,
                          price, is_active, created_at, updated_at
                """
            ),
            {**allowed, "service_id": service_id, "salon_id": salon["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Service not found")
        await self.session.commit()
        return self._service_response(row)

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
                       working_hours, is_active, created_at, updated_at
                from staff
                where salon_id = :salon_id
                order by is_active desc, name
                """
            ),
            {"salon_id": salon["id"]},
        )
        return [self._staff_response(row) for row in result.mappings().all()]

    async def create_owner_staff(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Create a staff member."""

        salon = await self.get_owner_salon(actor_id)
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
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            message = str(exc)
            if "not offered by this staff" in message.lower():
                raise ValidationError("Selected staff member does not offer this service") from exc
            if "slot" in message.lower() or "available" in message.lower():
                raise SlotUnavailableError("Selected slot is no longer available") from exc
            raise ConflictError("Booking could not be created") from exc

        booking = await self.get_booking(str(booking_id), values.get("actor_id"))
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def list_bookings(self, actor_id: str, role: str) -> list[dict[str, Any]]:
        """List bookings visible to an actor, enriched with salon and staff display fields."""

        if role == "customer":
            predicate = "b.customer_id = :actor_id"
        elif role in {"owner", "staff"}:
            predicate = """
              b.customer_id = :actor_id
              or exists (select 1 from salons s2 where s2.id = b.salon_id and s2.owner_id = :actor_id)
              or exists (select 1 from staff st2 where st2.id = b.staff_id and st2.profile_id = :actor_id)
            """
        else:
            predicate = "true"
        result = await self.session.execute(
            text(
                f"""
                select
                  b.id, b.salon_id, b.staff_id, b.customer_id,
                  b.customer_name, b.customer_phone, b.phone_verified,
                  b.source, b.status,
                  b.start_datetime, b.end_datetime,
                  b.total_duration_minutes, b.total_price,
                  b.payment_status, b.payment_method,
                  b.rejection_reason, b.notes,
                  b.created_at, b.updated_at,
                  s.name  as salon_name,
                  s.address as salon_address,
                  img.url as salon_image,
                  st.name as staff_name,
                  st.photo_url as staff_photo_url,
                  coalesce(
                    json_agg(json_build_object(
                      'service_id',       bs.service_id,
                      'service_name',     bs.service_name,
                      'duration_minutes', bs.duration_minutes,
                      'price',            bs.price
                    )) filter (where bs.service_id is not null),
                    '[]'::json
                  ) as services
                from bookings b
                join salons s on s.id = b.salon_id
                join staff  st on st.id = b.staff_id
                left join lateral (
                  select url from salon_images
                  where salon_id = b.salon_id
                  order by is_main desc, sort_order asc, created_at asc
                  limit 1
                ) img on true
                left join booking_services bs on bs.booking_id = b.id
                where {predicate}
                group by b.id, s.name, s.address, img.url, st.name, st.photo_url
                order by b.start_datetime desc
                """
            ),
            {"actor_id": actor_id},
        )
        rows = result.mappings().all()
        return [
            {
                **dict(row),
                "id": str(row["id"]),
                "salon_id": str(row["salon_id"]),
                "staff_id": str(row["staff_id"]),
                "customer_id": str(row["customer_id"]) if row.get("customer_id") else None,
            }
            for row in rows
        ]

    async def get_booking(self, booking_id: str, actor_id: str | None) -> dict[str, Any] | None:
        """Read one booking enriched with salon and staff display fields."""

        result = await self.session.execute(
            text(
                """
                select
                  b.id, b.salon_id, b.staff_id, b.customer_id,
                  b.customer_name, b.customer_phone, b.phone_verified,
                  b.source, b.status,
                  b.start_datetime, b.end_datetime,
                  b.total_duration_minutes, b.total_price,
                  b.payment_status, b.payment_method,
                  b.rejection_reason, b.notes,
                  b.created_at, b.updated_at,
                  s.name   as salon_name,
                  s.address as salon_address,
                  img.url  as salon_image,
                  st.name  as staff_name,
                  st.photo_url as staff_photo_url,
                  coalesce(
                    json_agg(json_build_object(
                      'service_id',       bs.service_id,
                      'service_name',     bs.service_name,
                      'duration_minutes', bs.duration_minutes,
                      'price',            bs.price
                    )) filter (where bs.service_id is not null),
                    '[]'::json
                  ) as services
                from bookings b
                join salons s  on s.id  = b.salon_id
                join staff  st on st.id = b.staff_id
                left join lateral (
                  select url from salon_images
                  where salon_id = b.salon_id
                  order by is_main desc, sort_order asc, created_at asc
                  limit 1
                ) img on true
                left join booking_services bs on bs.booking_id = b.id
                where b.id = :booking_id
                  and (
                    cast(:actor_id as uuid) is null
                    or b.customer_id = :actor_id
                    or exists (select 1 from salons s2 where s2.id = b.salon_id and s2.owner_id = :actor_id)
                    or exists (select 1 from staff st2 where st2.id = b.staff_id and st2.profile_id = :actor_id)
                  )
                group by b.id, s.name, s.address, img.url, st.name, st.photo_url
                """
            ),
            {"booking_id": booking_id, "actor_id": actor_id},
        )
        row = result.mappings().one_or_none()
        if not row:
            return None
        return {
            **dict(row),
            "id": str(row["id"]),
            "salon_id": str(row["salon_id"]),
            "staff_id": str(row["staff_id"]),
            "customer_id": str(row["customer_id"]) if row.get("customer_id") else None,
        }

    async def update_booking_status(
        self,
        actor_id: str,
        booking_id: str,
        status: str,
        *,
        rejection_reason: str | None = None,
        customer_only: bool = False,
    ) -> dict[str, Any]:
        """Update booking status if visible to the actor."""

        owner_predicate = """
          exists (select 1 from salons s where s.id = bookings.salon_id and s.owner_id = :actor_id)
          or exists (select 1 from staff st where st.id = bookings.staff_id and st.profile_id = :actor_id)
        """
        predicate = "customer_id = :actor_id" if customer_only else owner_predicate
        result = await self.session.execute(
            text(
                f"""
                update bookings
                set status = cast(:status as booking_status),
                    rejection_reason = coalesce(:rejection_reason, rejection_reason)
                where id = :booking_id and ({predicate})
                returning id
                """
            ),
            {
                "actor_id": actor_id,
                "booking_id": booking_id,
                "status": status,
                "rejection_reason": rejection_reason,
            },
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Booking not found")
        await self.session.commit()
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def record_payment(
        self, actor_id: str, booking_id: str, payment_method: str
    ) -> dict[str, Any]:
        """Record owner-side booking payment."""

        result = await self.session.execute(
            text(
                """
                update bookings
                set payment_status = 'paid',
                    payment_method = cast(:payment_method as payment_method)
                where id = :booking_id
                  and (
                    exists (select 1 from salons s where s.id = bookings.salon_id and s.owner_id = :actor_id)
                    or exists (select 1 from staff st where st.id = bookings.staff_id and st.profile_id = :actor_id)
                  )
                returning id
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id, "payment_method": payment_method},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Booking not found")
        await self.session.commit()
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def list_notifications(self, actor_id: str) -> list[dict[str, Any]]:
        """List actor notifications."""

        result = await self.session.execute(
            text(
                """
                select id, user_id, booking_id, type, title, body, read, read_at, created_at
                from notifications
                where user_id = :actor_id
                order by created_at desc
                """
            ),
            {"actor_id": actor_id},
        )
        rows = []
        for row in result.mappings().all():
            r = dict(row)
            for col in ("id", "user_id", "booking_id"):
                if r.get(col) is not None:
                    r[col] = str(r[col])
            rows.append(r)
        return rows

    async def mark_notification_read(self, actor_id: str, notification_id: str) -> dict[str, Any]:
        """Mark one notification as read."""

        result = await self.session.execute(
            text(
                """
                update notifications
                set read = true
                where id = :notification_id and user_id = :actor_id
                returning id, user_id, booking_id, type, title, body, read, read_at, created_at
                """
            ),
            {"actor_id": actor_id, "notification_id": notification_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Notification not found")
        await self.session.commit()
        r = dict(row)
        for col in ("id", "user_id", "booking_id"):
            if r.get(col) is not None:
                r[col] = str(r[col])
        return r

    # register_device with actor_id is defined in the section below (line ~1334)

    async def deactivate_device(self, token: str) -> None:
        """Deactivate this actor's device token through the database function."""

        await self.session.execute(
            text("select deactivate_device_token(:token)"),
            {"token": token},
        )
        await self.session.commit()

    async def deactivate_device_for_actor(self, actor_id: str, token: str) -> None:
        """Deactivate a device token only if it belongs to the given actor.

        Preferred over deactivate_device() when we have a verified actor_id,
        because the DB function relies on auth.uid() which is unavailable via
        the privileged Postgres role.
        """

        await self.session.execute(
            text(
                "update device_tokens set is_active = false where token = :token and user_id = :actor_id"
            ),
            {"token": token, "actor_id": actor_id},
        )
        await self.session.commit()

    # ------------------------------------------------------------------
    # Admin — salon management
    # ------------------------------------------------------------------

    async def admin_list_salons(
        self,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """List all salons (admin view, including inactive)."""

        result = await self.session.execute(
            text(
                """
                select s.id, s.owner_id, s.name, s.description, s.category,
                       s.address, s.city, s.timezone, s.approval_mode,
                       s.profile_completed, s.is_active, s.created_at, s.updated_at,
                       p.email as owner_email, p.full_name as owner_name
                from salons s
                join profiles p on p.id = s.owner_id
                where (:search is null or s.name ilike :search or p.email ilike :search)
                order by s.created_at desc
                limit :limit offset :offset
                """
            ),
            {
                "search": f"%{search}%" if search else None,
                "limit": limit,
                "offset": offset,
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def admin_get_salon(self, salon_id: str) -> dict[str, Any]:
        """Read one salon (admin view)."""

        result = await self.session.execute(
            text(
                """
                select s.*, p.email as owner_email, p.full_name as owner_name
                from salons s
                join profiles p on p.id = s.owner_id
                where s.id = :salon_id
                """
            ),
            {"salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        return dict(row)

    async def admin_create_salon(
        self,
        owner_user_id: str,
        salon_name: str,
        timezone: str,
    ) -> dict[str, Any]:
        """Create a new salon for the given owner profile."""

        result = await self.session.execute(
            text(
                """
                insert into salons (owner_id, name, timezone)
                values (:owner_id, :name, :timezone)
                returning id, owner_id, name, description, category, address, city,
                          lat, lng, timezone, working_hours, approval_mode,
                          slot_interval_minutes, qr_token, profile_completed,
                          is_active, created_at, updated_at
                """
            ),
            {"owner_id": owner_user_id, "name": salon_name, "timezone": timezone},
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def admin_update_salon(
        self, salon_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update admin-editable salon fields."""

        allowed = {k: v for k, v in values.items() if v is not None}
        if not allowed:
            return await self.admin_get_salon(salon_id)
        assignments = ", ".join(f"{k} = :{k}" for k in allowed)
        result = await self.session.execute(
            text(
                f"""
                update salons set {assignments}
                where id = :salon_id
                returning id, owner_id, name, description, category, address, city,
                          lat, lng, timezone, working_hours, approval_mode,
                          slot_interval_minutes, qr_token, profile_completed,
                          is_active, created_at, updated_at
                """
            ),
            {**allowed, "salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        await self.session.commit()
        return dict(row)

    async def admin_deactivate_salon(self, salon_id: str) -> dict[str, Any]:
        """Soft-delete a salon and return its owner_id for Supabase ban."""

        result = await self.session.execute(
            text(
                """
                update salons set is_active = false
                where id = :salon_id
                returning id, owner_id
                """
            ),
            {"salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        await self.session.execute(
            text("update profiles set is_active = false where id = :owner_id"),
            {"owner_id": str(row["owner_id"])},
        )
        await self.session.commit()
        return dict(row)

    # ------------------------------------------------------------------
    # Admin — catalog (service categories & subcategories)
    # ------------------------------------------------------------------

    async def list_categories(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        """List service categories."""

        where = "" if include_inactive else "where is_active"
        result = await self.session.execute(
            text(
                f"""
                select id, name, slug, image_url, description, sort_order, is_active,
                       created_at, updated_at
                from service_categories
                {where}
                order by sort_order, name
                """
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_category(self, category_id: str) -> dict[str, Any]:
        """Read one service category."""

        result = await self.session.execute(
            text(
                """
                select id, name, slug, image_url, description, sort_order, is_active,
                       created_at, updated_at
                from service_categories
                where id = :category_id
                """
            ),
            {"category_id": category_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Category not found")
        return dict(row)

    async def create_category(self, values: dict[str, Any]) -> dict[str, Any]:
        """Create a service category."""

        result = await self.session.execute(
            text(
                """
                insert into service_categories (name, slug, image_url, description, sort_order)
                values (:name, :slug, :image_url, :description, :sort_order)
                returning id, name, slug, image_url, description, sort_order, is_active,
                          created_at, updated_at
                """
            ),
            {
                "name": values["name"],
                "slug": values["slug"],
                "image_url": values.get("image_url"),
                "description": values.get("description"),
                "sort_order": values.get("sort_order", 0),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_category(
        self, category_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service category."""

        allowed = {k: v for k, v in values.items() if v is not None}
        if not allowed:
            return await self.get_category(category_id)
        assignments = ", ".join(f"{k} = :{k}" for k in allowed)
        result = await self.session.execute(
            text(
                f"""
                update service_categories set {assignments}
                where id = :category_id
                returning id, name, slug, image_url, description, sort_order, is_active,
                          created_at, updated_at
                """
            ),
            {**allowed, "category_id": category_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Category not found")
        await self.session.commit()
        return dict(row)

    async def deactivate_category(self, category_id: str) -> dict[str, Any]:
        """Soft-delete a service category."""

        return await self.update_category(category_id, {"is_active": False})

    async def list_subcategories(
        self, category_id: str, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        """List subcategories for a category."""

        where_active = "" if include_inactive else "and sc.is_active"
        result = await self.session.execute(
            text(
                f"""
                select sc.id, sc.category_id, sc.name, sc.slug, sc.image_url,
                       sc.description, sc.sort_order, sc.is_active,
                       sc.created_at, sc.updated_at
                from service_subcategories sc
                where sc.category_id = :category_id {where_active}
                order by sc.sort_order, sc.name
                """
            ),
            {"category_id": category_id},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_subcategory(self, subcategory_id: str) -> dict[str, Any]:
        """Read one subcategory."""

        result = await self.session.execute(
            text(
                """
                select id, category_id, name, slug, image_url, description,
                       sort_order, is_active, created_at, updated_at
                from service_subcategories
                where id = :subcategory_id
                """
            ),
            {"subcategory_id": subcategory_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subcategory not found")
        return dict(row)

    async def create_subcategory(self, values: dict[str, Any]) -> dict[str, Any]:
        """Create a service subcategory."""

        result = await self.session.execute(
            text(
                """
                insert into service_subcategories
                  (category_id, name, slug, image_url, description, sort_order)
                values
                  (:category_id, :name, :slug, :image_url, :description, :sort_order)
                returning id, category_id, name, slug, image_url, description,
                          sort_order, is_active, created_at, updated_at
                """
            ),
            {
                "category_id": values["category_id"],
                "name": values["name"],
                "slug": values["slug"],
                "image_url": values.get("image_url"),
                "description": values.get("description"),
                "sort_order": values.get("sort_order", 0),
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def update_subcategory(
        self, subcategory_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a service subcategory."""

        allowed = {k: v for k, v in values.items() if v is not None}
        if not allowed:
            return await self.get_subcategory(subcategory_id)
        assignments = ", ".join(f"{k} = :{k}" for k in allowed)
        result = await self.session.execute(
            text(
                f"""
                update service_subcategories set {assignments}
                where id = :subcategory_id
                returning id, category_id, name, slug, image_url, description,
                          sort_order, is_active, created_at, updated_at
                """
            ),
            {**allowed, "subcategory_id": subcategory_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Subcategory not found")
        await self.session.commit()
        return dict(row)

    async def deactivate_subcategory(self, subcategory_id: str) -> dict[str, Any]:
        """Soft-delete a service subcategory."""

        return await self.update_subcategory(subcategory_id, {"is_active": False})

    # ------------------------------------------------------------------
    # Staff languages
    # ------------------------------------------------------------------

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

    async def get_qr_image_url(self, salon_id: str) -> str | None:
        """Return the cached QR image URL from the salons table, or None if not yet set."""
        result = await self.session.execute(
            text("select qr_image_url from salons where id = :salon_id"),
            {"salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return row["qr_image_url"]  # may be None if column is NULL

    async def set_qr_image_url(self, salon_id: str, url: str) -> None:
        """Persist the QR image URL so future requests return immediately."""
        await self.session.execute(
            text(
                "update salons set qr_image_url = :url where id = :salon_id"
            ),
            {"salon_id": salon_id, "url": url},
        )
        await self.session.commit()

    async def validate_qr_token(self, qr_token: str) -> str:
        """Validate a QR token and return the salon_id (UUID as str).

        Lightweight alternative to get_salon_by_qr — used in the booking path
        where we only need to confirm the token is valid and get the salon_id.
        No services or staff are fetched.
        """

        result = await self.session.execute(
            text(
                """
                select id
                from get_salon_by_qr(:qr_token)
                """
            ),
            {"qr_token": qr_token},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found or not accepting walk-ins")
        return str(row["id"])

    async def get_salon_by_qr(self, qr_token: str) -> dict[str, Any]:
        """Return salon info via the get_salon_by_qr database function.

        The DB function validates the QR token (active + profile_completed).
        We then fetch the full salon row to include address and image_url,
        which are needed by the walk-in slot-first UI mini-header.
        """

        # Step 1: validate QR via the security-definer DB function
        result = await self.session.execute(
            text(
                """
                select id, name, description, city, timezone, approval_mode
                from get_salon_by_qr(:qr_token)
                """
            ),
            {"qr_token": qr_token},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found or not accepting walk-ins")
        salon = dict(row)

        # Step 2: fetch extra display fields from the salons table/image table
        extra = await self.session.execute(
            text(
                """
                select s.address, img.url as image_url
                from salons s
                left join lateral (
                  select url
                  from salon_images
                  where salon_id = s.id
                  order by is_main desc, sort_order asc, created_at asc
                  limit 1
                ) img on true
                where s.id = :salon_id
                """
            ),
            {"salon_id": str(salon["id"])},
        )
        extra_row = extra.mappings().one_or_none()
        if extra_row:
            salon["address"] = extra_row["address"]
            salon["image_url"] = extra_row["image_url"]

        salon["id"] = str(salon["id"])
        salon["services"] = await self.list_public_services(salon["id"])
        salon["staff"] = await self._list_walkin_staff(str(salon["id"]))
        return salon

    async def _list_walkin_staff(self, salon_id: str) -> list[dict[str, Any]]:
        """Return active staff for walk-in display."""

        result = await self.session.execute(
            text(
                """
                select id, name, photo_url, specialization
                from staff
                where salon_id = :salon_id and is_active
                order by name
                """
            ),
            {"salon_id": salon_id},
        )
        return [{**dict(row), "id": str(row["id"])} for row in result.mappings().all()]

    # ------------------------------------------------------------------
    # Fix: register_device now accepts the actor_id explicitly
    # ------------------------------------------------------------------

    async def register_device(
        self,
        actor_id: str,
        token: str,
        platform: str | None,
        device_name: str | None,
    ) -> dict[str, Any]:
        """Register (or reactivate) a device token, linked to actor_id."""

        # We use a direct upsert rather than the DB function so we can pass
        # the actor_id without relying on auth.uid() (which doesn't work via
        # the privileged Postgres role).
        result = await self.session.execute(
            text(
                """
                insert into device_tokens (user_id, token, platform, device_name, is_active, last_seen_at)
                values (:user_id, :token, :platform, :device_name, true, now())
                on conflict (token) do update
                  set user_id      = :user_id,
                      is_active    = true,
                      platform     = coalesce(:platform, device_tokens.platform),
                      device_name  = coalesce(:device_name, device_tokens.device_name),
                      last_seen_at = now()
                returning id, token, platform
                """
            ),
            {
                "user_id": actor_id,
                "token": token,
                "platform": platform,
                "device_name": device_name,
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())

    async def create_notification(
        self,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str | None,
    ) -> dict[str, Any]:
        """Create a notification record and return it."""

        result = await self.session.execute(
            text(
                """
                insert into notifications (user_id, booking_id, type, title, body)
                values (:user_id, :booking_id, :type, :title, :body)
                returning id, user_id, booking_id, type, title, body, read, read_at, created_at
                """
            ),
            {
                "user_id": user_id,
                "booking_id": booking_id,
                "type": notification_type,
                "title": title,
                "body": body,
            },
        )
        await self.session.commit()
        return dict(result.mappings().one())
