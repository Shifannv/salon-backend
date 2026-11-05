"""Public salon catalog reads."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
)
from app.infrastructure.db.repositories.platform._sql import (
    _contains_pattern,
)


class PublicCatalogMixin:
    """Public salon catalog reads."""

    session: AsyncSession

    async def create_salon_report(
        self, actor_id: str, salon_id: str, reason: str, details: str,
    ) -> dict[str, Any]:
        result = await self.session.execute(text("""
            insert into salon_reports (reporter_id, salon_id, reason, details)
            values (:actor_id, :salon_id, :reason, :details)
            returning id, status
        """), {"actor_id": actor_id, "salon_id": salon_id,
               "reason": reason, "details": details})
        row = dict(result.mappings().one())
        await self.session.commit()
        return row

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
        service: str | None = None,
        surface: str | None = None,
        shuffle_seed: str = "default",
    ) -> list[dict[str, Any]]:
        """List public approved, active, completed salons.

        ``search`` matches the salon name, city or address; ``city`` matches the city exactly but ignoring case;
        ``service`` keeps salons with at least one bookable service (active, in an active category and
        subcategory, staff-assigned) whose name or subcategory name matches. Matching is case-insensitive and ``%``/``_`` in the input are literal.

        Services are NOT bundled. Callers that need service data should use
        the dedicated GET /salons/{salon_id}/services endpoint.

        ``category`` filters to salons that have at least one active, staff-assigned
        service whose displayed category (owner label, or shared catalog fallback)
        matches the value (ILIKE wildcard).
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
            "surface": surface or ("search" if search or ids or category or service else "home"),
            "shuffle_seed": shuffle_seed,
            "search": _contains_pattern(search),
            "service": _contains_pattern(service),
            "city": city.strip() if city and city.strip() else None,
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
              s.id, s.name, s.address, s.city,
              s.lat, s.lng, s.timezone, s.approval_mode, s.accepting_bookings, s.profile_completed,
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
            left join lateral (
              select coalesce(max(sp.ranking_weight), 0) as weight
              from salon_subscriptions ss
              join subscription_plans sp on sp.id = ss.plan_id
              where ss.salon_id = s.id
                and is_subscription_promotion_active(
                      ss.status, ss.current_period_start,
                      ss.current_period_end, ss.grace_period_end)
            ) promo on true
            where s.is_active and s.profile_completed and s.approval_status = 'approved'
              and public.salon_booking_eligible(s.id)
              and s.discovery_visibility <> 'hidden'
              and (:surface <> 'home' or s.discovery_visibility = 'listed')
              and (cast(:search as text) is null
                   or s.name ilike cast(:search as text) escape '!'
                   or s.city ilike cast(:search as text) escape '!'
                   or s.address ilike cast(:search as text) escape '!')
              and (cast(:city as text) is null or lower(s.city) = lower(cast(:city as text)))
              and (cast(:service as text) is null or exists (
                select 1
                from services sv3
                join service_subcategories ss3 on ss3.id = sv3.subcategory_id
                join service_categories sc3 on sc3.id = ss3.category_id
                where sv3.salon_id = s.id
                  and sv3.is_active
                  and ss3.is_active
                  and sc3.is_active
                  and (sv3.name ilike cast(:service as text) escape '!'
                       or ss3.name ilike cast(:service as text) escape '!')
                  and exists (
                    select 1
                    from staff_services stsv3
                    join staff st3 on st3.id = stsv3.staff_id
                    where stsv3.service_id = sv3.id
                      and stsv3.is_active
                      and st3.is_active
                      and st3.salon_id = sv3.salon_id
                  )
              ))
              {ids_filter}
            group by s.id, img.url, promo.weight
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
                  and (coalesce(sv2.category_name, sv2.subcategory_name, ss2.name, sc2.name) ilike cast(:category_pattern as text)
                       or (sv2.category_name is null and sc2.name ilike cast(:category_pattern as text)))
                  and exists (
                    select 1
                    from staff_services stsv2
                    join staff st2 on st2.id = stsv2.staff_id
                    where stsv2.service_id = sv2.id
                      and stsv2.is_active
                      and st2.is_active
                      and st2.salon_id = sv2.salon_id
                  )
              )
            )
            order by case when :surface = 'home' then
                       case s.home_placement when 'top' then 0 when 'normal' then 1
                         when 'random' then 2 when 'below' then 3 end
                       else 1 end,
                     case when :surface = 'home' and s.home_placement = 'random'
                       then md5(cast(s.id as text) || :shuffle_seed) else '' end,
                     coalesce(promo.weight, 0) desc, s.display_priority desc,
                     distance_km asc nulls last, s.name asc, s.id asc
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

    async def assert_public_salon(self, salon_id: str) -> None:
        """Check current publication state; never authorize from a cached payload."""
        result = await self.session.execute(
            text("""
                select id from salons
                where id = :salon_id and is_active and profile_completed
                  and approval_status = 'approved' and public.salon_booking_eligible(id)
            """),
            {"salon_id": salon_id},
        )
        if result.mappings().one_or_none() is None:
            raise NotFoundError("Salon not found")

    async def get_public_salon(self, salon_id: str) -> dict[str, Any]:
        """Read public salon details (core fields + images only).

        Services and staff are NOT bundled here. Use the dedicated endpoints:
          - GET /salons/{salon_id}/services
          - GET /salons/{salon_id}/staff
        """

        result = await self.session.execute(
            text(
                """
                select id, name, address, city, lat, lng, timezone,
                       working_hours, approval_mode, slot_interval_minutes, accepting_bookings, profile_completed,
                       is_active
                from salons
                where id = :salon_id and is_active and profile_completed and approval_status = 'approved'
                  and public.salon_booking_eligible(id)
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

        await self.assert_public_salon(salon_id)

        result = await self.session.execute(
            text(
                """
                select st.id, st.name, st.photo_url, st.specialization, st.experience,
                  coalesce((select jsonb_agg(sv.id::text order by sv.name)
                    from staff_services ss join services sv on sv.id=ss.service_id
                    join service_subcategories sub on sub.id=sv.subcategory_id and sub.is_active
                    join service_categories cat on cat.id=sub.category_id and cat.is_active
                    where ss.staff_id=st.id and ss.is_active and sv.is_active and sv.salon_id=st.salon_id),'[]'::jsonb) as service_ids,
                  coalesce((select jsonb_agg(jsonb_build_object('service_id',sv.id,
                    'duration_minutes',coalesce(ss.duration_minutes,sv.duration_minutes),
                    'price',coalesce(ss.price_override,sv.price)) order by sv.name)
                    from staff_services ss join services sv on sv.id=ss.service_id
                    join service_subcategories sub on sub.id=sv.subcategory_id and sub.is_active
                    join service_categories cat on cat.id=sub.category_id and cat.is_active
                    where ss.staff_id=st.id and ss.is_active and sv.is_active and sv.salon_id=st.salon_id),'[]'::jsonb) as services,
                  coalesce((select jsonb_agg(distinct l.name) from staff_service_languages ssl
                    join languages l on l.code=ssl.language_code join staff_services ss on ss.id=ssl.staff_service_id
                    join services sv on sv.id=ss.service_id
                    join service_subcategories sub on sub.id=sv.subcategory_id and sub.is_active
                    join service_categories cat on cat.id=sub.category_id and cat.is_active
                    where ss.staff_id=st.id and ss.is_active and sv.is_active and sv.salon_id=st.salon_id),'[]'::jsonb) as languages
                from staff st
                where st.salon_id = :salon_id and st.is_active
                order by name
                """
            ),
            {"salon_id": salon_id},
        )
        rows = result.mappings().all()
        return [{**dict(row), "id": str(row["id"])} for row in rows]

    async def list_public_services(self, salon_id: str) -> list[dict[str, Any]]:
        """List public active services for a salon."""

        await self.assert_public_salon(salon_id)

        result = await self.session.execute(
            text(
                """
                select sv.id, sv.salon_id, sv.subcategory_id, sv.name,
                       sv.duration_minutes, sv.price, sv.is_active,
                       to_jsonb(sv)->>'menu_category_id' as menu_category_id,
                       case when to_jsonb(sv) ? 'selection_group' then to_jsonb(sv)->>'selection_group' else '__category__' end as selection_group,
                       coalesce(sv.category_name, sv.subcategory_name, ss.name, sc.name) as category_name,
                       coalesce(sv.subcategory_name, ss.name) as subcategory_name, sv.photo_url
                from services sv
                join service_subcategories ss on ss.id = sv.subcategory_id
                join service_categories sc on sc.id = ss.category_id
                where sv.salon_id = :salon_id
                  and exists (select 1 from salons sl where sl.id = sv.salon_id
                              and sl.is_active and sl.profile_completed
                              and sl.approval_status = 'approved' and public.salon_booking_eligible(sl.id))
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
                select sv.id, sv.salon_id, sv.subcategory_id, sv.name,
                       sv.duration_minutes, sv.price, sv.is_active,
                       to_jsonb(sv)->>'menu_category_id' as menu_category_id,
                       case when to_jsonb(sv) ? 'selection_group' then to_jsonb(sv)->>'selection_group' else '__category__' end as selection_group,
                       coalesce(sv.category_name, sv.subcategory_name, ss.name, sc.name) as category_name,
                       coalesce(sv.subcategory_name, ss.name) as subcategory_name, sv.photo_url
                from services sv
                join service_subcategories ss on ss.id = sv.subcategory_id
                join service_categories sc on sc.id = ss.category_id
                where sv.salon_id in (
                    select value::uuid
                    from jsonb_array_elements_text(cast(:salon_ids_json as jsonb)) value
                )
                  and exists (select 1 from salons sl where sl.id = sv.salon_id
                              and sl.is_active and sl.profile_completed
                              and sl.approval_status = 'approved')
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
