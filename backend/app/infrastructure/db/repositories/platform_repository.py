"""Raw SQL repository adapter for frontend-facing platform APIs."""

import hashlib
import json
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.salon_photos import validate_salon_photo_write, visible_salon_photos
from app.core.config import settings
from app.core.exceptions import (
    BookingIdempotencyKeyReusedError,
    ConflictError,
    IdempotencyKeyReuseError,
    NotFoundError,
    PayAtSalonBlockedError,
    PayAtSalonDailyLimitError,
    PaymentCollectionRequiredError,
    PaymentInProgressError,
    PaymentOvercollectionError,
    QrCodeNotFoundError,
    SalonNotAcceptingBookingsError,
    SlotUnavailableError,
    ValidationError,
)

# SQLSTATEs the booking SQL deliberately raises to reject a request: P0001 from
# `raise exception '...'` in create_booking, 23514 from the guard_booking_checkout trigger
# (migrations/sql/0035_booking_checkout_safety.sql).
_BUSINESS_ERROR_SQLSTATES = frozenset({"P0001", "23514"})


def _is_business_error(exc: BaseException) -> bool:
    """True when the database rejected the request on purpose, not because it failed."""

    return isinstance(exc, DBAPIError) and getattr(exc.orig, "sqlstate", None) in _BUSINESS_ERROR_SQLSTATES


def _contains_pattern(value: str | None) -> str | None:
    """Build a literal "contains" ILIKE pattern (escape char ``!``); blank input means no filter."""

    text_value = (value or "").strip()
    if not text_value:
        return None
    escaped = text_value.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped}%"


def _canonical_json_value(value: Any) -> str:
    """Serialize non-JSON values; aware datetimes become UTC so one instant has one spelling."""

    if isinstance(value, datetime) and value.utcoffset() is not None:
        return value.astimezone(UTC).isoformat()
    return str(value)


def _request_fingerprint(values: dict[str, Any]) -> str:
    """SHA-256 of a booking request, equal for the same instant sent with different UTC offsets."""

    payload = json.dumps(values, sort_keys=True, default=_canonical_json_value)
    return hashlib.sha256(payload.encode()).hexdigest()


class PlatformRepository:
    """Database adapter for customer and salon-owner use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_media_url(self, url: str) -> None:
        """Serialize reference writes and cleanup across API/worker processes."""
        if "/webp-v2/" in url:
            # All members share a lock before their individual URL locks. No new
            # schema is needed; direct client media assignment remains guarded by 0020.
            family = url.rsplit("/", 1)[0] + "/"
            await self.session.execute(
                text("select pg_advisory_xact_lock(hashtextextended(:url, 0))"), {"url": family},
            )
        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtextextended(:url, 0))"), {"url": url},
        )

    async def media_reference_guards_installed(self) -> bool:
        """Cleanup requires enabled DB guards, including direct Data API writes."""
        result = await self.session.execute(text("""
            select count(*) = 7
            from pg_trigger t
            join pg_class c on c.oid = t.tgrelid
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = current_schema() and t.tgname = 'media_reference_guard'
              and t.tgenabled in ('O', 'A') and not t.tgisinternal
              and c.relname in ('profiles', 'staff', 'salon_images', 'services',
                                'service_categories', 'service_subcategories', 'salons')
        """))
        return bool(result.scalar_one())

    async def media_url_is_referenced(self, url: str) -> bool:
        """Include inactive records: soft deletion must not destroy shared media."""
        # This does not bypass RLS. A role whose policies would hide references
        # gets an error instead of a dangerously incomplete cleanup decision.
        await self.session.execute(text("set local row_security = off"))
        result = await self.session.execute(text("""
            select exists (
                select 1 from profiles where avatar_url = :url
                union all select 1 from staff where photo_url = :url
                union all select 1 from salon_images where url = :url and is_active = true
                union all select 1 from services where photo_url = :url
                union all select 1 from service_categories where image_url = :url
                union all select 1 from service_subcategories where image_url = :url
                union all select 1 from salons where qr_image_url = :url
            )
        """), {"url": url})
        return bool(result.scalar_one())

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
              s.id, s.name, s.category, s.address, s.city,
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
                  and coalesce(sv2.category_name, sc2.name) ilike cast(:category_pattern as text)
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
                select id, name, category, address, city, lat, lng, timezone,
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

        await self.get_public_salon(salon_id)

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

        await self.get_public_salon(salon_id)

        result = await self.session.execute(
            text(
                """
                select sv.id, sv.salon_id, sv.subcategory_id, sv.name,
                       sv.duration_minutes, sv.price, sv.is_active,
                       coalesce(sv.category_name, sc.name) as category_name,
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
                       coalesce(sv.category_name, sc.name) as category_name,
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

    async def list_salon_images(self, salon_id: str) -> list[dict[str, Any]]:
        """One cover and at most two distinct slides, including legacy read protection."""
        return visible_salon_photos(await self._list_salon_images_raw(salon_id))

    async def _list_salon_images_raw(self, salon_id: str) -> list[dict[str, Any]]:
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

    async def get_workspace_salon(self, actor_id: str) -> dict[str, Any] | None:
        """Read workspace state without auto-provisioning a salon."""
        result = await self.session.execute(
            text("""
                select s.id, s.name, s.qr_token, s.is_active, s.profile_completed, s.approval_status
                from salons s
                where s.owner_id = :actor_id
                   or exists (select 1 from staff st where st.salon_id = s.id
                              and st.profile_id = :actor_id and st.is_active)
                order by s.is_active desc, s.created_at asc
                limit 1
            """),
            {"actor_id": actor_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

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
        if salon.get("approved_by") is not None:
            salon["approved_by"] = str(salon["approved_by"])
        salon["images"] = await self.list_salon_images(salon["id"])
        return salon

    async def _get_owner_salon_row(self, actor_id: str):
        """Raw DB read — returns the mapping row or None, never raises."""

        result = await self.session.execute(
            text(
                """
                select id, owner_id, name, category, address, city, lat, lng,
                       timezone, working_hours, approval_mode, slot_interval_minutes, accepting_bookings,
                       qr_token, profile_completed, approval_status, approved_at, approved_by,
                          rejection_reason, is_active, created_at, updated_at
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
                returning id, owner_id, name, category, address, city, lat, lng,
                          timezone, working_hours, approval_mode, slot_interval_minutes, accepting_bookings,
                          qr_token, profile_completed, approval_status, approved_at, approved_by,
                          rejection_reason, is_active, created_at, updated_at
                """
            ),
            {"actor_id": actor_id},
        )
        await self.session.commit()
        return await self._owner_salon_with_images(result.mappings().one())

    async def _owner_salon_id(self, actor_id: str) -> str:
        """Return the id of the owner's active salon, provisioning a blank one if needed."""

        row = await self._get_owner_salon_row(actor_id)
        if row is None:
            return str((await self.provision_owner_salon(actor_id))["id"])
        return str(row["id"])

    async def _find_owner_salon_id(self, actor_id: str) -> str | None:
        """Read-only salon resolver: the owner's active salon id, or None.

        Unlike ``_owner_salon_id`` this never provisions (and never commits), so a
        ``GET`` cannot create a salon row as a side effect.
        """

        row = await self._get_owner_salon_row(actor_id)
        return None if row is None else str(row["id"])

    async def get_payout_account(self, actor_id: str) -> dict[str, Any] | None:
        """Return the owner's payout row with the account number already masked.

        The projection to ``bank_account_last4`` happens inside Postgres
        (``salon_payout_account_masked``), so the full number is never read into Python.
        Does not provision a salon: an owner with no salon simply has no payout row.
        """

        salon_id = await self._find_owner_salon_id(actor_id)
        if salon_id is None:
            return None
        result = await self.session.execute(
            text("select * from salon_payout_account_masked(:salon_id)"),
            {"salon_id": salon_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def update_payout_account(
        self,
        actor_id: str,
        values: dict[str, Any],
        validate: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        """Merge ``values`` into the owner's payout row entirely inside SQL.

        Omitted fields keep their stored value; an explicit ``None`` clears the field.
        ``validate`` receives the merged *view* in which the stored account number is
        represented only by a presence marker, so Python never holds the full value and
        ``validate`` may raise ``ValidationError``. A per-salon advisory lock serialises
        writers.
        """

        salon_id = await self._owner_salon_id(actor_id)
        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"payout:{salon_id}"},
        )
        current = await self.get_payout_account(actor_id) or {}
        view: dict[str, Any] = {
            "account_holder_name": current.get("account_holder_name"),
            "upi_id": current.get("upi_id"),
            "bank_name": current.get("bank_name"),
            "ifsc": current.get("ifsc"),
            # Presence marker only; never the stored number.
            "bank_account_number": "stored" if current.get("bank_account_last4") else None,
        }
        view.update({k: v for k, v in values.items() if k in view})

        fields = ("account_holder_name", "upi_id", "bank_name", "bank_account_number", "ifsc")
        written = {k: v for k, v in values.items() if k in fields}
        if "bank_account_number" in values and values["bank_account_number"] is None:
            # Clearing the account number takes the dependent bank fields with it unless the
            # caller says otherwise (ck_payout_bank_triple: they cannot stand alone).
            for dependent in ("ifsc", "bank_name"):
                if dependent not in values:
                    view[dependent] = None
                    written[dependent] = None
        validate(view)
        params: dict[str, Any] = {"salon_id": salon_id}
        for field in fields:
            params[field] = written.get(field)
            params[f"set_{field}"] = field in written
        await self.session.execute(
            text(
                """
                insert into salon_payout_accounts
                  (salon_id, account_holder_name, upi_id, bank_name, bank_account_number, ifsc)
                values
                  (:salon_id, :account_holder_name, :upi_id, :bank_name,
                   :bank_account_number, :ifsc)
                on conflict (salon_id) do update set
                  account_holder_name = case when cast(:set_account_holder_name as boolean)
                    then excluded.account_holder_name
                    else salon_payout_accounts.account_holder_name end,
                  upi_id = case when cast(:set_upi_id as boolean)
                    then excluded.upi_id else salon_payout_accounts.upi_id end,
                  bank_name = case when cast(:set_bank_name as boolean)
                    then excluded.bank_name else salon_payout_accounts.bank_name end,
                  bank_account_number = case when cast(:set_bank_account_number as boolean)
                    then excluded.bank_account_number
                    else salon_payout_accounts.bank_account_number end,
                  ifsc = case when cast(:set_ifsc as boolean)
                    then excluded.ifsc else salon_payout_accounts.ifsc end
                """
            ),
            params,
        )
        row = await self.get_payout_account(actor_id)
        await self.session.commit()
        if row is None:  # pragma: no cover - the upsert above guarantees a row
            raise NotFoundError("Payout account not found")
        return row

    async def list_payout_account_history(
        self, actor_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return the owner's payout change history (last four digits only)."""

        salon_id = await self._find_owner_salon_id(actor_id)
        if salon_id is None:
            return []
        result = await self.session.execute(
            text(
                """
                select h.id, h.changed_at, h.action, h.changed_fields,
                       h.before_state as before_state, h.after_state as after_state,
                       p.full_name as changed_by_name
                from salon_payout_account_history h
                left join profiles p on p.id = h.changed_by
                where h.salon_id = :salon_id
                order by h.changed_at desc, h.id desc
                limit :limit
                """
            ),
            {"salon_id": salon_id, "limit": limit},
        )
        rows = [dict(row) for row in result.mappings().all()]
        for row in rows:
            for key in ("before_state", "after_state"):
                if isinstance(row.get(key), str):
                    row[key] = json.loads(row[key])
        return rows

    async def get_setup_facts(self, actor_id: str) -> dict[str, Any]:
        """Return the raw facts behind the owner setup checklist in one query.

        Read-only: an owner who has no salon yet gets all-empty facts rather than a
        freshly provisioned row.
        """

        salon_id = await self._find_owner_salon_id(actor_id)
        if salon_id is None:
            return {
                "name": None, "category": None, "address": None, "city": None,
                "working_hours": None, "has_photos": False, "has_services": False,
                "has_staff": False, "has_payout": False,
            }
        result = await self.session.execute(
            text(
                """
                select s.name, s.category, s.address, s.city, s.working_hours,
                       exists (select 1 from salon_images i
                               where i.salon_id = s.id and i.is_active) as has_photos,
                       exists (select 1 from services sv
                               where sv.salon_id = s.id and sv.is_active) as has_services,
                       exists (select 1 from staff st
                               where st.salon_id = s.id and st.is_active) as has_staff,
                       exists (select 1 from salon_payout_accounts p
                               where p.salon_id = s.id) as has_payout
                from salons s
                where s.id = :salon_id
                """
            ),
            {"salon_id": salon_id},
        )
        return dict(result.mappings().one())

    async def update_owner_salon(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Update owner-editable salon fields."""

        if "description" in values:
            raise ValidationError("Unsupported salon field")
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
                returning id, owner_id, name, category, address, city, lat, lng,
                          timezone, working_hours, approval_mode, slot_interval_minutes, accepting_bookings,
                          qr_token, profile_completed, approval_status, approved_at, approved_by,
                          rejection_reason, is_active, created_at, updated_at
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
        """Submit onboarding for review; a rejected salon may be resubmitted."""

        if "description" in (values or {}):
            raise ValidationError("Unsupported salon field")
        allowed = self._prepare_jsonb_values(dict(values or {}))
        payload = {**allowed, "profile_completed": True}

        await self._lock_owner_salon(actor_id)
        salon = await self._get_owner_salon_row(actor_id)
        if salon is not None:
            locked = await self.session.execute(
                text("select approval_status from salons where id = :id for update"),
                {"id": salon["id"]},
            )
            salon = {**salon, "approval_status": locked.scalar_one()}
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
                    returning id, owner_id, name, category, address, city, lat, lng,
                              timezone, working_hours, approval_mode, slot_interval_minutes, accepting_bookings,
                              qr_token, profile_completed, approval_status, approved_at, approved_by,
                          rejection_reason, is_active, created_at, updated_at
                    """
                ),
                params,
            )
            await self.session.commit()
            return await self._owner_salon_with_images(result.mappings().one())

        if salon["approval_status"] == "rejected":
            payload.update(approval_status="pending", approved_at=None, approved_by=None,
                           rejection_reason=None)

        assignments = ", ".join(self._sql_assignment(key) for key in payload)
        result = await self.session.execute(
            text(
                f"""
                update salons
                set {assignments}
                where id = :salon_id and owner_id = :actor_id and is_active
                returning id, owner_id, name, category, address, city, lat, lng,
                          timezone, working_hours, approval_mode, slot_interval_minutes, accepting_bookings,
                          qr_token, profile_completed, approval_status, approved_at, approved_by,
                          rejection_reason, is_active, created_at, updated_at
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
        await self.session.execute(text("select id from salons where id = :id for update"), {"id": salon["id"]})
        # The publication use case holds the URL advisory lock. A lost attach
        # response can safely retry without inserting a duplicate gallery row.
        existing = await self.session.execute(text("""
            select id, salon_id, url, caption, is_main, sort_order, created_at, updated_at
            from salon_images where salon_id = :salon_id and url = :url and is_active = true
            limit 1
        """), {"salon_id": salon["id"], "url": values["url"]})
        row = existing.mappings().one_or_none()
        if row is not None:
            if bool(row.get("is_main")) != bool(values.get("is_main", False)):
                raise ValidationError("Choose a different photo for each salon image")
            await self.session.commit()
            return dict(row)
        validate_salon_photo_write(await self._list_salon_images_raw(salon["id"]), values)
        result = await self._execute_salon_photo_write(
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
        await self.session.execute(text("select id from salons where id = :id for update"), {"id": salon["id"]})
        images = await self._list_salon_images_raw(salon["id"])
        if not any(str(image["id"]) == image_id for image in images):
            raise NotFoundError("Image not found")
        allowed = {key: value for key, value in values.items() if value is not None}
        if not allowed:
            return next(image for image in images if str(image["id"]) == image_id)
        validate_salon_photo_write(images, allowed, image_id)
        assignments = ", ".join(f"{key} = :{key}" for key in allowed)
        result = await self._execute_salon_photo_write(
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

    async def _execute_salon_photo_write(self, statement: Any, values: dict[str, Any]) -> Any:
        """Map only known photo constraints; never expose raw database errors."""
        try:
            return await self.session.execute(statement, values)
        except DBAPIError as error:
            await self.session.rollback()
            state = getattr(error.orig, "sqlstate", None)
            diagnostic = str(error.orig)
            if state == "23505" and "uq_salon_active_image_url" in diagnostic:
                raise ValidationError("Choose a different photo for each salon image") from None
            if state == "23514" and any(code in diagnostic for code in ("salon_photo_limit", "salon_photo_move_forbidden")):
                raise ValidationError("A salon supports one cover and at most two gallery photos; refresh and try again") from None
            if state == "40001":
                raise ConflictError("Salon photos changed; refresh and try again") from None
            raise

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
                       sv.created_at, sv.updated_at,
                       coalesce(sv.category_name, sc.name) as category_name,
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

    async def create_owner_service(self, actor_id: str, values: dict[str, Any]) -> dict[str, Any]:
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
        await self.session.commit()
        service_id = str(result.scalar_one())
        return await self._get_service_with_categories(service_id)

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
                       sv.created_at, sv.updated_at,
                       coalesce(sv.category_name, sc.name) as category_name,
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
            "is_active", "category_name", "subcategory_name", "photo_url",
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
               if key not in {"category_name", "subcategory_name", "photo_url"}):
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
            from app.core.exceptions import AppError
            if isinstance(exc, AppError) or not _is_business_error(exc):
                # Outages, timeouts and unexpected errors surface as 500, never as a 409.
                raise
            message = str(exc)
            if "pay_at_salon_daily_limit" in message:
                raise PayAtSalonDailyLimitError("You can keep only 1 active Pay at Salon booking per day.") from exc
            if "pay_at_salon_temporarily_blocked" in message:
                raise PayAtSalonBlockedError("Pay at Salon is blocked for 7 days after two no-shows. Online payment remains available where enabled.") from exc
            if "salon_not_accepting_bookings" in message:
                raise SalonNotAcceptingBookingsError(
                    "This salon is not accepting bookings right now"
                ) from exc
            if "not offered by this staff" in message.lower():
                raise ValidationError("Selected staff member does not offer this service") from exc
            if "slot" in message.lower() or "available" in message.lower():
                raise SlotUnavailableError("Selected slot is no longer available") from exc
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

    async def list_bookings(
        self,
        actor_id: str,
        role: str,
        *,
        booking_status: str | None = None,
        source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List bookings visible to an actor, enriched with salon and staff display fields."""

        if role == "customer":
            predicate = "b.customer_id = :actor_id"
        elif role in {"owner", "staff"}:
            # Workspace roles only see their own salon: personal bookings the actor made
            # as a customer at other salons must not leak into owner analytics/inbox.
            predicate = """
              exists (select 1 from salons s2 where s2.id = b.salon_id and s2.owner_id = :actor_id)
              or exists (
                select 1 from staff st2
                where st2.salon_id = b.salon_id
                  and st2.profile_id = :actor_id and st2.is_active
              )
            """
        else:
            predicate = "true"

        filters = [f"({predicate})"]
        params: dict[str, Any] = {"actor_id": actor_id}
        if booking_status is not None:
            filters.append("b.status = cast(:booking_status as booking_status)")
            params["booking_status"] = booking_status
        if source is not None:
            filters.append("b.source = cast(:source as booking_source)")
            params["source"] = source
        if date_from is not None:
            filters.append(
                "b.start_datetime >= (cast(cast(:date_from as date) as timestamp) AT TIME ZONE s.timezone)"
            )
            params["date_from"] = date_from
        if date_to is not None:
            filters.append(
                "b.start_datetime < ((cast(:date_to as date) + interval '1 day') AT TIME ZONE s.timezone)"
            )
            params["date_to"] = date_to

        pagination = ""
        if limit is not None:
            pagination = "limit :limit offset :offset"
            params.update({"limit": limit, "offset": offset})

        result = await self.session.execute(
            text(
                f"""
                select
                  b.id, b.salon_id, b.staff_id, b.customer_id,
                  b.customer_name, b.customer_phone, b.phone_verified,
                  b.source, b.status,
                  b.start_datetime, b.end_datetime, b.estimated_end_datetime,
                  b.total_duration_minutes, b.total_price,
                  case when b.payment_preference <> 'pay_at_salon' and b.checkout_policy_version = 'customer_processing_v1' then round(b.total_price * 0.05, 2) else 0 end as online_processing_charge,
                  b.payment_status, b.payment_method, b.payment_preference,
                  b.currency, b.deposit_amount, b.paid_amount, b.refunded_amount,
                  b.rejection_reason, b.cancellation_reason, b.notes,
                  b.created_at, b.updated_at,
                  s.name  as salon_name,
                  s.owner_id as salon_owner_id,
                  s.address as salon_address,
                  img.url as salon_image,
                  st.name as staff_name,
                  st.photo_url as staff_photo_url,
                  (
                    select ar.status from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'payment_confirmation'
                    order by ar.created_at desc limit 1
                  ) as latest_payment_request_status,
                  (
                    select ar.decision from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'payment_confirmation'
                    order by ar.created_at desc limit 1
                  ) as latest_payment_request_decision,
                  (
                    select coalesce(ar.decision_reason, ar.reason)
                    from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'payment_confirmation'
                    order by ar.created_at desc limit 1
                  ) as latest_payment_request_reason,
                  (
                    select ar.status from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'cancellation'
                    order by ar.created_at desc limit 1
                  ) as latest_cancellation_request_status,
                  (
                    select ar.decision from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'cancellation'
                    order by ar.created_at desc limit 1
                  ) as latest_cancellation_request_decision,
                  (
                    select coalesce(ar.decision_reason, ar.reason)
                    from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'cancellation'
                    order by ar.created_at desc limit 1
                  ) as latest_cancellation_request_reason,
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
                where {' and '.join(filters)}
                group by b.id, s.name, s.owner_id, s.address, img.url, st.name, st.photo_url
                order by b.start_datetime desc
                {pagination}
                """
            ),
            params,
        )
        rows = result.mappings().all()
        return [
            {
                **dict(row),
                "id": str(row["id"]),
                "salon_id": str(row["salon_id"]),
                "staff_id": str(row["staff_id"]),
                "customer_id": str(row["customer_id"]) if row.get("customer_id") else None,
                "salon_owner_id": str(row["salon_owner_id"]),
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
                  b.start_datetime, b.end_datetime, b.estimated_end_datetime,
                  b.total_duration_minutes, b.total_price,
                  case when b.payment_preference <> 'pay_at_salon' and b.checkout_policy_version = 'customer_processing_v1' then round(b.total_price * 0.05, 2) else 0 end as online_processing_charge,
                  b.payment_status, b.payment_method, b.payment_preference,
                  b.currency, b.deposit_amount, b.paid_amount, b.refunded_amount,
                  b.rejection_reason, b.cancellation_reason, b.notes,
                  b.created_at, b.updated_at,
                  s.name   as salon_name,
                  s.owner_id as salon_owner_id,
                  s.address as salon_address,
                  img.url  as salon_image,
                  st.name  as staff_name,
                  st.photo_url as staff_photo_url,
                  (
                    select ar.status from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'payment_confirmation'
                    order by ar.created_at desc limit 1
                  ) as latest_payment_request_status,
                  (
                    select ar.decision from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'payment_confirmation'
                    order by ar.created_at desc limit 1
                  ) as latest_payment_request_decision,
                  (
                    select coalesce(ar.decision_reason, ar.reason)
                    from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'payment_confirmation'
                    order by ar.created_at desc limit 1
                  ) as latest_payment_request_reason,
                  (
                    select ar.status from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'cancellation'
                    order by ar.created_at desc limit 1
                  ) as latest_cancellation_request_status,
                  (
                    select ar.decision from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'cancellation'
                    order by ar.created_at desc limit 1
                  ) as latest_cancellation_request_decision,
                  (
                    select coalesce(ar.decision_reason, ar.reason)
                    from booking_action_requests ar
                    where ar.booking_id = b.id and ar.kind = 'cancellation'
                    order by ar.created_at desc limit 1
                  ) as latest_cancellation_request_reason,
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
                    or exists (
                      select 1 from staff st2
                      where st2.salon_id = b.salon_id
                        and st2.profile_id = :actor_id and st2.is_active
                    )
                  )
                group by b.id, s.name, s.owner_id, s.address, img.url, st.name, st.photo_url
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
            "salon_owner_id": str(row["salon_owner_id"]),
        }

    async def update_booking_status(
        self,
        actor_id: str,
        booking_id: str,
        status: str,
        *,
        rejection_reason: str | None = None,
        cancellation_reason: str | None = None,
        customer_only: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Apply an authorized, valid booking transition under a row lock."""
        scope = f"booking:{booking_id}:{status}"
        replay = await self.begin_booking_operation(actor_id, scope, idempotency_key, {
            "status": status, "rejection_reason": rejection_reason, "cancellation_reason": cancellation_reason,
        })
        if replay is not None:
            return replay

        owner_predicate = """
          exists (select 1 from salons s where s.id = bookings.salon_id and s.owner_id = :actor_id)
          or exists (select 1 from staff st where st.id = bookings.staff_id and st.profile_id = :actor_id and st.is_active)
        """
        predicate = "customer_id = :actor_id" if customer_only else owner_predicate
        current_result = await self.session.execute(
            text(
                f"""
                select id, status, customer_id, customer_name, payment_status, payment_preference,
                       start_datetime, now() as database_now from bookings
                where id = :booking_id and ({predicate})
                for update
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        current = current_result.mappings().one_or_none()
        if current is None:
            raise NotFoundError("Booking not found")
        allowed = {
            "pending": {"confirmed", "rejected", "cancelled"},
            "confirmed": {"checked_in", "completed", "cancelled", "no_show"},
            "checked_in": {"completed", "cancelled", "no_show"},
        }
        if status not in allowed.get(current["status"], set()):
            raise ConflictError("Booking state changed; refresh before deciding")
        if status == "no_show" and current["start_datetime"] > current["database_now"]:
            raise ValidationError("A customer cannot be marked as a no-show before the appointment starts")
        if status == "completed" and current.get("payment_preference") == "pay_at_salon" and current.get("payment_status") != "paid":
            raise PaymentCollectionRequiredError("Collect cash or direct UPI from customer before completing service.")

        await self.session.execute(
            text(
                """
                update bookings
                set status = cast(:status as booking_status),
                    rejection_reason = coalesce(:rejection_reason, rejection_reason),
                    cancellation_reason = coalesce(:cancellation_reason, cancellation_reason)
                where id = :booking_id
                """
            ),
            {
                "actor_id": actor_id,
                "booking_id": booking_id,
                "status": status,
                "rejection_reason": rejection_reason,
                "cancellation_reason": cancellation_reason,
            },
        )
        if status in {"rejected", "cancelled", "completed"}:
            invalidated_kinds = (
                ["cancellation"]
                if status == "completed"
                else ["cancellation", "payment_confirmation"]
            )
            await self.session.execute(
                text(
                    """
                    update booking_action_requests
                    set status = 'resolved',
                        decision = 'invalidated',
                        decision_reason = :reason,
                        resolved_by = :actor_id,
                        resolved_at = now()
                    where booking_id = :booking_id
                      and status = 'pending'
                      and kind in (
                        select value
                        from jsonb_array_elements_text(cast(:kinds_json as jsonb)) value
                      )
                    """
                ),
                {
                    "actor_id": actor_id,
                    "booking_id": booking_id,
                    "kinds_json": json.dumps(invalidated_kinds),
                    "reason": f"Booking changed to {status}",
                },
            )
        outbox_ids: list[str] = []
        if status == "cancelled" and current["customer_id"]:
            outbox_ids.append(
                await self._insert_notification_outbox(
                    user_id=str(current["customer_id"]),
                    booking_id=booking_id,
                    notification_type="booking_cancelled",
                    title="Booking cancelled by salon",
                    body=(
                        "The salon cancelled your appointment: "
                        f"{cancellation_reason or 'Please contact the salon for details.'}"
                    ),
                )
            )
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        booking["_outbox_ids"] = outbox_ids
        await self.finish_booking_operation(actor_id, scope, idempotency_key, booking)
        await self.session.commit()
        return booking

    async def cancel_customer_booking(
        self,
        actor_id: str,
        booking_id: str,
        cancellation_reason: str | None,
        cutoff_minutes: int,
    ) -> dict[str, Any]:
        """Cancel an owned booking before the server cancellation cutoff."""

        result = await self.session.execute(
            text(
                """
                select b.id, b.status, b.start_datetime, b.customer_name,
                       s.owner_id,
                       now() as database_now
                from bookings b
                join salons s on s.id = b.salon_id
                where b.id = :booking_id and b.customer_id = :actor_id
                for update of b
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Booking not found")
        if row["status"] not in {"pending", "confirmed"}:
            raise ConflictError("Booking can no longer be cancelled")
        cutoff = row["start_datetime"] - timedelta(minutes=cutoff_minutes)
        if row["database_now"] >= cutoff:
            raise ConflictError(
                "Immediate cancellation cutoff has passed; submit a cancellation request"
            )

        await self.session.execute(
            text(
                """
                update bookings
                set status = 'cancelled', cancellation_reason = :cancellation_reason
                where id = :booking_id
                """
            ),
            {
                "booking_id": booking_id,
                "cancellation_reason": cancellation_reason,
            },
        )
        await self.session.execute(
            text(
                """
                update booking_action_requests
                set status = 'resolved', decision = 'invalidated',
                    decision_reason = 'Booking cancelled directly by customer',
                    resolved_by = :actor_id, resolved_at = now()
                where booking_id = :booking_id and status = 'pending'
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        outbox_id = await self._insert_notification_outbox(
            user_id=str(row["owner_id"]),
            booking_id=booking_id,
            notification_type="booking_cancelled",
            title="Booking cancelled",
            body=f"{row['customer_name']} cancelled their appointment.",
        )
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        booking["_outbox_ids"] = [outbox_id]
        await self.session.commit()
        return booking

    async def delay_booking(
        self,
        actor_id: str,
        booking_id: str,
        estimated_end_datetime: datetime,
    ) -> dict[str, Any]:
        """Set an estimated completion time for an owner/staff-visible booking."""

        result = await self.session.execute(
            text(
                """
                update bookings
                set estimated_end_datetime = :estimated_end_datetime
                where id = :booking_id
                  and status in ('pending', 'confirmed')
                  and (
                    exists (
                      select 1 from salons s
                      where s.id = bookings.salon_id and s.owner_id = :actor_id
                    )
                    or exists (
                      select 1 from staff st
                      where st.id = bookings.staff_id and st.profile_id = :actor_id
                        and st.is_active
                    )
                  )
                returning id
                """
            ),
            {
                "actor_id": actor_id,
                "booking_id": booking_id,
                "estimated_end_datetime": estimated_end_datetime,
            },
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError("Active booking not found")
        await self.session.commit()
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def list_delay_affected_bookings(
        self, booking_id: str, estimated_end_datetime: datetime
    ) -> list[dict[str, Any]]:
        """Return later customer bookings that overlap a delayed completion estimate."""

        result = await self.session.execute(
            text(
                """
                select affected.id, affected.customer_id, affected.start_datetime
                from bookings current_booking
                join bookings affected
                  on affected.staff_id = current_booking.staff_id
                 and affected.id <> current_booking.id
                 and affected.status in ('pending', 'confirmed')
                 and affected.start_datetime >= current_booking.end_datetime
                 and affected.start_datetime < :estimated_end_datetime
                where current_booking.id = :booking_id
                  and affected.customer_id is not null
                order by affected.start_datetime
                """
            ),
            {
                "booking_id": booking_id,
                "estimated_end_datetime": estimated_end_datetime,
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def _insert_manual_payment(
        self, *, booking_id: str, actor_id: str, method: str
    ) -> None:
        """Write the manual receipt as a ledger row; the trigger settles payment_status.

        The caller must hold the booking row lock. The amount is whatever the ledger says is
        still outstanding, so recording the balance after an online deposit settles exactly
        the remainder (and can never over-collect: the database raises
        ``payment_overcollection`` otherwise).
        """

        gateway_open = await self.session.execute(
            text(
                """
                select 1 from booking_payments
                where booking_id = :booking_id and channel = 'gateway'
                  and status in ('created', 'authorized')
                limit 1
                """
            ),
            {"booking_id": booking_id},
        )
        if gateway_open.first() is not None:
            raise PaymentInProgressError(
                "An online payment is in progress for this booking; wait for it to settle "
                "or ask the customer to cancel it"
            )
        try:
            await self.session.execute(
                text(
                    """
                    insert into booking_payments
                      (booking_id, salon_id, payer_id, recorded_by, channel, purpose,
                       settlement_model, method, amount, currency, status, intent_reference,
                       captured_at, collection_method, collected_by_owner)
                    select b.id, b.salon_id, b.customer_id, :actor_id, 'manual',
                           case when b.paid_amount - b.refunded_amount > 0
                                then 'balance' else 'full' end,
                           'offline', case when cast(:method as text) = 'cash' then 'cash' else 'online' end,
                           greatest(b.total_price - (b.paid_amount - b.refunded_amount), 0),
                           b.currency, 'captured', 'manual:' || gen_random_uuid()::text, now(),
                           case when cast(:method as text) = 'cash' then 'CASH' else 'UPI_DIRECT' end,
                           exists(select 1 from salons s where s.id=b.salon_id and s.owner_id=:actor_id)
                    from bookings b
                    where b.id = :booking_id
                    """
                ),
                {"booking_id": booking_id, "actor_id": actor_id, "method": method},
            )
        except DBAPIError as exc:
            await self.session.rollback()
            if "payment_overcollection" in str(exc):
                raise PaymentOvercollectionError(
                    "This payment would collect more than the booking total"
                ) from exc
            raise

    async def record_payment(
        self, actor_id: str, booking_id: str, payment_method: str, *, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        """Record an eligible owner-side payment exactly once."""
        scope = f"booking:{booking_id}:collect"
        replay = await self.begin_booking_operation(actor_id, scope, idempotency_key, {"method": payment_method})
        if replay is not None:
            return replay

        result = await self.session.execute(
            text(
                """
                select b.id, b.status, b.payment_status, b.customer_id
                from bookings b
                where b.id = :booking_id
                  and (
                    exists (select 1 from salons s where s.id = b.salon_id and s.owner_id = :actor_id)
                    or exists (select 1 from staff st where st.id = b.staff_id and st.profile_id = :actor_id and st.is_active)
                  )
                for update of b
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Booking not found")
        if row["status"] not in {"confirmed", "checked_in", "completed"}:
            raise ConflictError("Only confirmed or completed bookings can be paid")
        if row["payment_status"] == "paid":
            raise ConflictError("Payment has already been recorded")

        await self._insert_manual_payment(
            booking_id=booking_id,
            actor_id=actor_id,
            method=payment_method,
        )
        await self.session.execute(
            text(
                """
                update booking_action_requests
                set status = 'resolved', decision = 'received',
                    decision_reason = 'Payment recorded directly by salon',
                    resolved_by = :actor_id, resolved_at = now()
                where booking_id = :booking_id
                  and kind = 'payment_confirmation'
                  and status = 'pending'
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        outbox_ids: list[str] = []
        if row["customer_id"]:
            outbox_ids.append(
                await self._insert_notification_outbox(
                    user_id=str(row["customer_id"]),
                    booking_id=booking_id,
                    notification_type="payment_received",
                    title="Payment received",
                    body="The salon recorded your payment and receipt.",
                )
            )
        booking = await self.get_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        booking["_outbox_ids"] = outbox_ids
        await self.finish_booking_operation(actor_id, scope, idempotency_key, booking)
        await self.session.commit()
        return booking

    async def _insert_notification_outbox(
        self,
        *,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Persist a notification and retryable push event in this transaction."""

        result = await self.session.execute(
            text(
                """
                with created_notification as (
                  insert into notifications (user_id, booking_id, type, title, body, data)
                  values (:user_id, :booking_id, :notification_type, :title, :body,
                          cast(:data as jsonb))
                  returning id, user_id
                )
                insert into notification_outbox (notification_id, user_id)
                select id, user_id from created_notification
                returning id
                """
            ),
            {
                "user_id": user_id,
                "booking_id": booking_id,
                "notification_type": notification_type,
                "title": title,
                "body": body,
                "data": json.dumps(data) if data else None,
            },
        )
        return str(result.scalar_one())

    async def enqueue_notification(
        self,
        *,
        user_id: str,
        booking_id: str | None,
        notification_type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Persist a notification/outbox pair outside another state transaction."""

        outbox_id = await self._insert_notification_outbox(
            user_id=user_id,
            booking_id=booking_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )
        await self.session.commit()
        return outbox_id

    async def _get_booking_action_request_row(
        self, request_id: str
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                select
                  ar.id, ar.booking_id, ar.kind, ar.status, ar.reason,
                  ar.decision, ar.decision_reason, ar.resolved_at, ar.created_at,
                  b.customer_name, b.start_datetime, b.total_price,
                  coalesce(
                    array(
                      select bs.service_name
                      from booking_services bs
                      where bs.booking_id = b.id
                      order by bs.service_name
                    ), array[]::text[]
                  ) as service_names
                from booking_action_requests ar
                join bookings b on b.id = ar.booking_id
                where ar.id = :request_id
                """
            ),
            {"request_id": request_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        item = dict(row)
        item["id"] = str(item["id"])
        item["booking_id"] = str(item["booking_id"])
        return item

    async def create_booking_action_request(
        self,
        actor_id: str,
        booking_id: str,
        kind: str,
        reason: str | None,
        *,
        cancellation_cutoff_minutes: int,
        allow_late_cancellation_requests: bool,
    ) -> dict[str, Any]:
        """Create an eligible customer request under a booking row lock."""

        result = await self.session.execute(
            text(
                """
                select b.id, b.status, b.payment_status, b.payment_preference,
                       b.start_datetime, b.end_datetime, b.customer_name,
                       s.owner_id, now() as database_now
                from bookings b
                join salons s on s.id = b.salon_id
                where b.id = :booking_id and b.customer_id = :actor_id
                for update of b
                """
            ),
            {"actor_id": actor_id, "booking_id": booking_id},
        )
        booking = result.mappings().one_or_none()
        if booking is None:
            raise NotFoundError("Booking not found")

        if kind == "payment_confirmation":
            if booking["status"] not in {"confirmed", "completed"}:
                raise ConflictError(
                    "Payment confirmation is allowed only for confirmed or completed bookings"
                )
            if booking["payment_status"] != "unpaid":
                raise ConflictError("Payment has already been recorded")
            if booking["payment_preference"] != "pay_at_salon":
                raise ConflictError("Booking is not configured for Pay at Salon")
            if booking["database_now"] < booking["start_datetime"]:
                raise ConflictError(
                    "Payment can be confirmed only after the salon visit starts"
                )
            title = "Customer reports payment"
            body = f"{booking['customer_name']} says they paid at the salon."
            notification_type = "payment_confirmation_requested"
        elif kind == "cancellation":
            if not allow_late_cancellation_requests:
                raise ConflictError("Late cancellation requests are disabled")
            if booking["status"] not in {"pending", "confirmed"}:
                raise ConflictError("Booking can no longer be cancelled")
            if booking["database_now"] >= booking["end_datetime"]:
                raise ConflictError("The appointment has already ended")
            cutoff = booking["start_datetime"] - timedelta(
                minutes=cancellation_cutoff_minutes
            )
            if booking["database_now"] < cutoff:
                raise ConflictError(
                    "Use immediate cancellation before the cancellation cutoff"
                )
            title = "Cancellation approval requested"
            body = f"{booking['customer_name']} requested a late cancellation."
            notification_type = "cancellation_requested"
        else:
            raise ValidationError("Unsupported booking action request kind")

        pending = await self.session.execute(
            text(
                """
                select id from booking_action_requests
                where booking_id = :booking_id and kind = :kind and status = 'pending'
                """
            ),
            {"booking_id": booking_id, "kind": kind},
        )
        if pending.scalar_one_or_none() is not None:
            raise ConflictError("A pending request already exists for this booking")

        created = await self.session.execute(
            text(
                """
                insert into booking_action_requests (
                  booking_id, kind, reason, requested_by, created_by, updated_by
                ) values (
                  :booking_id, :kind, :reason, :actor_id, :actor_id, :actor_id
                )
                returning id
                """
            ),
            {
                "booking_id": booking_id,
                "kind": kind,
                "reason": (reason or "").strip() or None,
                "actor_id": actor_id,
            },
        )
        request_id = str(created.scalar_one())
        outbox_id = await self._insert_notification_outbox(
            user_id=str(booking["owner_id"]),
            booking_id=booking_id,
            notification_type=notification_type,
            title=title,
            body=body,
        )
        item = await self._get_booking_action_request_row(request_id)
        if item is None:
            raise NotFoundError("Booking action request not found")
        item["_outbox_ids"] = [outbox_id]
        await self.session.commit()
        return item

    async def list_booking_action_requests(
        self, actor_id: str, request_status: str | None
    ) -> list[dict[str, Any]]:
        """List action requests visible to an owner or salon staff member."""

        result = await self.session.execute(
            text(
                """
                select
                  ar.id, ar.booking_id, ar.kind, ar.status, ar.reason,
                  ar.decision, ar.decision_reason, ar.resolved_at, ar.created_at,
                  b.customer_name, b.start_datetime, b.total_price,
                  coalesce(
                    array(
                      select bs.service_name from booking_services bs
                      where bs.booking_id = b.id order by bs.service_name
                    ), array[]::text[]
                  ) as service_names
                from booking_action_requests ar
                join bookings b on b.id = ar.booking_id
                join salons s on s.id = b.salon_id
                where (cast(:request_status as text) is null
                       or ar.status::text = cast(:request_status as text))
                  and (
                    s.owner_id = :actor_id
                    or exists (
                      select 1 from staff access_staff
                      where access_staff.salon_id = b.salon_id
                        and access_staff.profile_id = :actor_id
                        and access_staff.is_active
                    )
                  )
                order by ar.created_at
                """
            ),
            {"actor_id": actor_id, "request_status": request_status},
        )
        items = []
        for row in result.mappings().all():
            item = dict(row)
            item["id"] = str(item["id"])
            item["booking_id"] = str(item["booking_id"])
            items.append(item)
        return items

    async def respond_booking_action_request(
        self,
        actor_id: str,
        request_id: str,
        decision: str,
        reason: str | None,
        payment_method: str = "cash",
    ) -> dict[str, Any]:
        """Resolve one request and transition its booking atomically."""

        result = await self.session.execute(
            text(
                """
                select ar.id, ar.kind, ar.status as request_status, ar.reason,
                       b.id as booking_id, b.status as booking_status,
                       b.payment_status, b.customer_id, b.end_datetime,
                       now() as database_now
                from booking_action_requests ar
                join bookings b on b.id = ar.booking_id
                join salons s on s.id = b.salon_id
                where ar.id = :request_id
                  and (
                    s.owner_id = :actor_id
                    or exists (
                      select 1 from staff access_staff
                      where access_staff.salon_id = b.salon_id
                        and access_staff.profile_id = :actor_id
                        and access_staff.is_active
                    )
                  )
                for update of b
                """
            ),
            {"actor_id": actor_id, "request_id": request_id},
        )
        current = result.mappings().one_or_none()
        if current is None:
            raise NotFoundError("Booking action request not found")
        if current["request_status"] != "pending":
            raise ConflictError("This request has already been resolved")
        request_lock = await self.session.execute(
            text(
                """
                select status from booking_action_requests
                where id = :request_id
                for update
                """
            ),
            {"request_id": request_id},
        )
        locked_request = request_lock.mappings().one_or_none()
        if locked_request is None or locked_request["status"] != "pending":
            raise ConflictError("This request has already been resolved")

        normalized_reason = (reason or "").strip() or None
        if current["kind"] == "payment_confirmation":
            if decision not in {"received", "not_received"}:
                raise ValidationError("Payment requests accept received or not_received")
            if current["booking_status"] not in {"confirmed", "completed"}:
                raise ConflictError("Booking is no longer eligible for payment")
            if current["payment_status"] != "unpaid":
                raise ConflictError("Payment has already been recorded")
            if decision == "received":
                # The method is the salon's statement of how the customer actually paid;
                # it used to be hardcoded to 'cash'.
                await self._insert_manual_payment(
                    booking_id=str(current["booking_id"]),
                    actor_id=actor_id,
                    method=payment_method,
                )
                title = "Payment received"
                body = (
                    "The salon confirmed your cash payment. Your receipt is recorded."
                    if payment_method == "cash"
                    else "The salon confirmed your payment. Your receipt is recorded."
                )
                notification_type = "payment_received"
            else:
                title = "Payment not received"
                body = normalized_reason or (
                    "The salon could not confirm your payment. You can try again after checking with them."
                )
                notification_type = "payment_not_received"
        else:
            if decision not in {"approve", "decline"}:
                raise ValidationError("Cancellation requests accept approve or decline")
            if current["booking_status"] not in {"pending", "confirmed"}:
                raise ConflictError("Booking is no longer eligible for cancellation")
            if current["database_now"] >= current["end_datetime"]:
                raise ConflictError("The appointment has already ended")
            if decision == "decline" and normalized_reason is None:
                raise ValidationError("A reason is required when declining cancellation")
            if decision == "approve":
                cancellation_reason = current["reason"] or (
                    "Late cancellation approved by salon"
                )
                await self.session.execute(
                    text(
                        """
                        update bookings
                        set status = 'cancelled', cancellation_reason = :reason
                        where id = :booking_id
                          and status in ('pending', 'confirmed')
                        """
                    ),
                    {
                        "booking_id": current["booking_id"],
                        "reason": cancellation_reason,
                    },
                )
                await self.session.execute(
                    text(
                        """
                        update booking_action_requests
                        set status = 'resolved', decision = 'invalidated',
                            decision_reason = 'Booking cancellation was approved',
                            resolved_by = :actor_id, resolved_at = now()
                        where booking_id = :booking_id
                          and id <> :request_id
                          and status = 'pending'
                        """
                    ),
                    {
                        "actor_id": actor_id,
                        "booking_id": current["booking_id"],
                        "request_id": request_id,
                    },
                )
                title = "Cancellation approved"
                body = "The salon approved your cancellation and released the appointment."
                notification_type = "cancellation_approved"
            else:
                title = "Cancellation declined"
                body = normalized_reason
                notification_type = "cancellation_declined"

        # Persist the decision message that the customer receives, even when
        # the owner did not provide an optional explanation.
        decision_reason = normalized_reason or body
        await self.session.execute(
            text(
                """
                update booking_action_requests
                set status = 'resolved', decision = :decision,
                    decision_reason = :reason, resolved_by = :actor_id,
                    resolved_at = now()
                where id = :request_id and status = 'pending'
                """
            ),
            {
                "request_id": request_id,
                "decision": decision,
                "reason": decision_reason,
                "actor_id": actor_id,
            },
        )
        outbox_id = await self._insert_notification_outbox(
            user_id=str(current["customer_id"]),
            booking_id=str(current["booking_id"]),
            notification_type=notification_type,
            title=title,
            body=body,
        )
        item = await self._get_booking_action_request_row(request_id)
        if item is None:
            raise NotFoundError("Booking action request not found")
        booking = await self.get_booking(str(current["booking_id"]), actor_id)
        item["booking"] = booking
        item["_outbox_ids"] = [outbox_id]
        await self.session.commit()
        return item

    async def get_notification_outbox_event(
        self, outbox_id: str
    ) -> dict[str, Any] | None:
        """Claim a due outbox event for one background delivery attempt."""

        result = await self.session.execute(
            text(
                """
                update notification_outbox
                set attempts = attempts + 1,
                    next_attempt_at = now() + interval '5 minutes'
                where id = :outbox_id
                  and status = 'pending'
                  and next_attempt_at <= now()
                returning id, notification_id, user_id
                """
            ),
            {"outbox_id": outbox_id},
        )
        row = result.mappings().one_or_none()
        await self.session.commit()
        if row is None:
            return None
        return {key: str(value) for key, value in dict(row).items()}

    async def list_due_notification_outbox_ids(self, limit: int = 50) -> list[str]:
        """Find persisted push events due for an attempt or retry."""

        result = await self.session.execute(
            text(
                """
                select id from notification_outbox
                where status = 'pending' and next_attempt_at <= now()
                order by next_attempt_at, created_at
                limit :limit
                """
            ),
            {"limit": limit},
        )
        return [str(row[0]) for row in result.all()]

    async def notification_has_failed_delivery(self, notification_id: str) -> bool:
        """Detect provider failures for still-active device tokens."""

        result = await self.session.execute(
            text(
                """
                select exists (
                  select 1 from notification_deliveries delivery
                  join device_tokens device on device.id = delivery.device_token_id
                  where delivery.notification_id = :notification_id
                    and not delivery.delivered
                    and device.is_active
                )
                """
            ),
            {"notification_id": notification_id},
        )
        return bool(result.scalar_one())

    async def mark_notification_outbox_processed(self, outbox_id: str) -> None:
        """Mark an outbox event processed after push fan-out returns."""

        await self.session.execute(
            text(
                """
                update notification_outbox
                set status = 'processed', processed_at = now(), last_error = null
                where id = :outbox_id
                """
            ),
            {"outbox_id": outbox_id},
        )
        await self.session.commit()

    async def mark_notification_outbox_retry(
        self, outbox_id: str, error: str
    ) -> None:
        """Persist a safe failure message and leave the event retryable."""

        await self.session.execute(
            text(
                """
                update notification_outbox
                set last_error = :error,
                    next_attempt_at = now() + interval '5 minutes'
                where id = :outbox_id and status = 'pending'
                """
            ),
            {"outbox_id": outbox_id, "error": error[:1000]},
        )
        await self.session.commit()

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
                           where bs.booking_id = b.id order by bs.service_name
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

    async def mark_all_notifications_read(self, actor_id: str) -> int:
        """Mark every unread notification owned by an actor."""

        result = await self.session.execute(
            text(
                """
                with updated as (
                  update notifications
                  set read = true
                  where user_id = :actor_id and not read
                  returning 1
                )
                select count(*) from updated
                """
            ),
            {"actor_id": actor_id},
        )
        updated_count = int(result.scalar_one())
        await self.session.commit()
        return updated_count

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
        approval_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all salons (admin view, including inactive)."""

        result = await self.session.execute(
            text(
                """
                select s.id, s.owner_id, s.name, s.category,
                       s.address, s.city, s.qr_token, s.timezone, s.approval_mode,
                       s.lat, s.lng, s.working_hours, s.slot_interval_minutes,
                       s.profile_completed, s.approval_status, s.approved_at, s.approved_by,
                       s.rejection_reason, s.display_priority, s.discovery_visibility,
                       s.home_placement, s.is_active, s.created_at, s.updated_at, s.updated_by,
                       p.email as owner_email, p.full_name as owner_name,
                       p.phone as owner_phone, p.avatar_url as owner_avatar_url,
                       p.phone_verified as owner_phone_verified, p.is_active as owner_is_active
                from salons s
                join profiles p on p.id = s.owner_id
                where (cast(:search as text) is null or s.name ilike :search or p.email ilike :search)
                  and (cast(:approval_status as text) is null
                       or s.approval_status = cast(:approval_status as salon_approval_status))
                order by s.created_at desc
                limit :limit offset :offset
                """
            ),
            {
                "search": f"%{search}%" if search else None,
                "limit": limit,
                "offset": offset,
                "approval_status": approval_status,
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def admin_get_salon(self, salon_id: str) -> dict[str, Any]:
        """Read one salon (admin view)."""

        result = await self.session.execute(
            text(
                """
                select s.*, p.email as owner_email, p.full_name as owner_name,
                       p.phone as owner_phone, p.avatar_url as owner_avatar_url,
                       p.phone_verified as owner_phone_verified, p.is_active as owner_is_active
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

    async def admin_get_onboarding(self, salon_id: str) -> dict[str, Any]:
        """Read private onboarding data without applying public approval filters."""
        salon = await self.admin_get_salon(salon_id)
        salon["images"] = await self.list_salon_images(salon_id)
        services = await self.session.execute(
            text("""
                select sv.*, coalesce(sv.category_name, sc.name) as category_name,
                       coalesce(sv.subcategory_name, ss.name) as subcategory_name
                from services sv
                left join service_subcategories ss on ss.id = sv.subcategory_id
                left join service_categories sc on sc.id = ss.category_id
                where sv.salon_id = :salon_id order by sv.name, sv.id
            """), {"salon_id": salon_id},
        )
        salon["services"] = [self._service_response(row) for row in services.mappings().all()]
        staff = await self.session.execute(
            text("select * from staff where salon_id = :salon_id order by name, id"),
            {"salon_id": salon_id},
        )
        salon["staff"] = [self._staff_response(row) for row in staff.mappings().all()]
        return salon

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
                returning id, owner_id, name, category, address, city,
                          lat, lng, timezone, working_hours, approval_mode,
                          slot_interval_minutes, qr_token, profile_completed,
                          approval_status, approved_at, approved_by, rejection_reason, is_active, created_at, updated_at
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
                returning id
                """
            ),
            {**allowed, "salon_id": salon_id},
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError("Salon not found")
        await self.session.commit()
        return await self.admin_get_salon(salon_id)

    async def admin_set_salon_approval(
        self, salon_id: str, approval_status: str, actor_id: str, reason: str | None
    ) -> dict[str, Any]:
        """Write the decision atomically; preserve the first approval timestamp on retries."""
        result = await self.session.execute(
            text("""
                update salons
                set approval_status = cast(:approval_status as salon_approval_status),
                    approved_at = case when :approval_status = 'approved'
                        then coalesce(approved_at, now()) else null end,
                    approved_by = case when :approval_status = 'approved'
                        then coalesce(approved_by, cast(:actor_id as uuid)) else null end,
                    rejection_reason = :reason
                where id = :salon_id and is_active and profile_completed
                returning id
            """),
            {"salon_id": salon_id, "approval_status": approval_status,
             "actor_id": actor_id, "reason": reason},
        )
        if result.scalar_one_or_none() is None:
            raise ConflictError("Salon is no longer eligible for review")
        await self.session.commit()
        return await self.admin_get_salon(salon_id)

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
            raise QrCodeNotFoundError("Salon not found or not accepting walk-ins")
        return str(row["id"])

    async def get_salon_by_qr(self, qr_token: str) -> dict[str, Any]:
        """Return salon info via the get_salon_by_qr database function.

        The DB function validates approval, activity, and profile completion.
        We then fetch the full salon row to include address and image_url,
        which are needed by the walk-in slot-first UI mini-header.
        """

        # Step 1: validate QR via the security-definer DB function
        result = await self.session.execute(
            text(
                """
                select id, name, city, timezone, approval_mode
                from get_salon_by_qr(:qr_token)
                """
            ),
            {"qr_token": qr_token},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise QrCodeNotFoundError("Salon not found or not accepting walk-ins")
        salon = dict(row)
        salon["qr_token"] = qr_token

        # Step 2: fetch extra display fields from the salons table/image table
        extra = await self.session.execute(
            text(
                """
                select s.address, s.working_hours, s.accepting_bookings, img.url as image_url
                from salons s
                left join lateral (
                  select url
                  from salon_images
                  where salon_id = s.id
                    and is_active = true
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
            salon["working_hours"] = extra_row["working_hours"]
            salon["accepting_bookings"] = extra_row["accepting_bookings"]

        salon["id"] = str(salon["id"])
        salon["images"] = await self.list_salon_images(salon["id"])
        salon["services"] = await self.list_public_services(salon["id"])
        salon["staff"] = await self._list_walkin_staff(str(salon["id"]))
        return salon

    async def _list_walkin_staff(self, salon_id: str) -> list[dict[str, Any]]:
        """Return active staff for walk-in display."""

        result = await self.session.execute(
            text(
                """
                select st.id, st.name, st.photo_url, st.specialization,
                       array(select cast(ss.service_id as text)
                             from staff_services ss join services sv on sv.id = ss.service_id
                             where ss.staff_id = st.id and ss.is_active and sv.is_active
                               and sv.salon_id = st.salon_id
                             order by ss.service_id) as service_ids
                from staff st
                where st.salon_id = :salon_id and st.is_active
                order by st.name
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
