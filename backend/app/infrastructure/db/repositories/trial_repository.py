"""Trial updates reuse salon_access and the existing booking eligibility rules."""

from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.services.trial_limits import (
    DEFAULT_TRIAL_DAYS,
    TrialLimits,
)


class SalonTrialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_trial(self, salon_id: str) -> dict[str, Any]:
        result = await self.session.execute(text("""
            select s.id as salon_id, a.trial_started_at, a.trial_ends_at,
              case when a.trial_started_at is null then :default_days
                   else ceil(extract(epoch from (a.trial_ends_at-a.trial_started_at))/86400)::int
                   end as trial_days,
              a.trial_booking_limit as trial_booking_limit,
              coalesce(a.bookings_counted, 0) as bookings_counted,
              a.trial_limit_reached_at,
              case when a.trial_started_at is null then 'not_started'
                   when a.trial_ends_at <= now() then 'expired'
                   when a.bookings_counted >= a.trial_booking_limit then 'quota_reached'
                   else 'active' end as state
            from salons s left join salon_access a on a.salon_id=s.id where s.id=:salon
        """), {"salon": salon_id, "default_days": DEFAULT_TRIAL_DAYS})
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Salon not found")
        return dict(row)

    async def apply_limits(self, salon_id: str, limits: TrialLimits, actor_id: str) -> None:
        """Caller owns the transaction and salon/access locks. No commit here."""
        result = await self.session.execute(text("""
            with usage as (
              select a.salon_id, greatest(a.bookings_counted, (
                select count(*) from (
                  select 1 from bookings b where b.salon_id=a.salon_id
                    and b.created_at >= a.trial_started_at limit :bookings
                ) counted
              ))::int as used
              from salon_access a where a.salon_id=:salon
            )
            update salon_access a set
              trial_ends_at=trial_started_at + (:days * interval '1 day'),
              trial_booking_limit=:bookings,
              bookings_counted=usage.used,
              trial_limit_reached_at=case when usage.used >= :bookings
                then coalesce(trial_limit_reached_at, now()) else null end,
              trial_ended_reason=case
                when trial_started_at + (:days * interval '1 day') <= now() then 'date'
                when usage.used >= :bookings then 'booking_limit' else null end,
              updated_at=now()
            from usage where a.salon_id=usage.salon_id and a.trial_started_at is not null
            returning a.salon_id
        """), {"salon": salon_id, "days": limits.days, "bookings": limits.bookings})
        if result.scalar_one_or_none() is None:
            raise ConflictError("The trial has not started; choose its limits when approving the salon")
        # No FK or personal-data column: the existing authenticated actor context also audits writes.
        await self.session.execute(text("""
            insert into subscription_events(provider_name, provider_event_reference, event_type,
              payload_hash, processing_status, processed_at)
            values ('admin', :reference, 'admin_trial_limits_set',
              encode(sha256(convert_to(:audit, 'UTF8')), 'hex'), 'processed', now())
        """), {"reference": f"trial-limits:{uuid4()}",
               "audit": f"{salon_id}:{actor_id}:{limits.days}:{limits.bookings}"})

    async def update_trial(
        self, salon_id: str, limits: TrialLimits, actor_id: str
    ) -> dict[str, Any]:
        salon = (await self.session.execute(text(
            "select is_active from salons where id=:salon for no key update"
        ), {"salon": salon_id})).scalar_one_or_none()
        if salon is None:
            raise NotFoundError("Salon not found")
        if not salon:
            raise ConflictError("Reactivate the salon before changing its trial")
        await self.session.execute(text(
            "select salon_id from salon_access where salon_id=:salon for update"
        ), {"salon": salon_id})
        await self.apply_limits(salon_id, limits, actor_id)
        await self.session.commit()
        return await self.get_trial(salon_id)
