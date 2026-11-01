"""Admin salon management."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.domain.services.trial_limits import TrialLimits
from app.infrastructure.db.repositories.trial_repository import SalonTrialRepository


class AdminSalonsMixin:
    """Admin salon management."""

    session: AsyncSession

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
                select s.id, s.owner_id, s.name,
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
                returning id, owner_id, name, address, city,
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
        self, salon_id: str, approval_status: str, actor_id: str, reason: str | None,
        *, trial_limits: TrialLimits | None = None,
    ) -> dict[str, Any]:
        """Write the decision atomically; preserve the first approval timestamp on retries."""
        first_trial = False
        if approval_status == "approved":
            await self.session.execute(text(
                "select id from salons where id=:salon for no key update"
            ), {"salon": salon_id})
            started = (await self.session.execute(text(
                "select trial_started_at from salon_access where salon_id=:salon for update"
            ), {"salon": salon_id})).scalar_one_or_none()
            first_trial = started is None
            if first_trial and trial_limits is None:
                # No platform default: the admin sets each salon's booking limit when approving it.
                await self.session.rollback()
                raise ValidationError("Choose the trial booking limit when approving this salon")
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
        if first_trial:
            # The existing approval trigger starts the trial. Override its initial allowance
            # before the same transaction commits; retries preserve already-granted trials.
            await SalonTrialRepository(self.session).apply_limits(salon_id, trial_limits, actor_id)
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

    async def admin_reactivate_salon(self, salon_id: str) -> dict[str, Any]:
        """Reactivate a salon and its local owner profile atomically."""

        result = await self.session.execute(
            text(
                """
                update salons set is_active = true
                where id = :salon_id
                returning owner_id
                """
            ),
            {"salon_id": salon_id},
        )
        owner_id = result.scalar_one_or_none()
        if owner_id is None:
            raise NotFoundError("Salon not found")
        await self.session.execute(
            text("update profiles set is_active = true where id = :owner_id"),
            {"owner_id": str(owner_id)},
        )
        await self.session.commit()
        return await self.admin_get_salon(salon_id)

    # ------------------------------------------------------------------
    # Admin — catalog (service categories & subcategories)
    # ------------------------------------------------------------------
