"""Booking list and detail reads."""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.platform._sql import page_bounds


class BookingQueriesMixin:
    """Booking list and detail reads."""

    session: AsyncSession

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

        params.update(page_bounds(limit, offset))

        result = await self.session.execute(
            text(
                f"""
                select
                  b.id, b.salon_id, b.staff_id, b.customer_id,
                  b.customer_name, b.customer_phone, b.phone_verified,
                  b.source, b.status,
                  b.start_datetime, b.end_datetime, b.estimated_end_datetime,
                  b.total_duration_minutes, b.total_price, b.checkout_policy_version,
                  coalesce((select jsonb_agg(part.value || jsonb_build_object('staff_name',person.name) order by (part.value->>'ordinal')::int)
                    from jsonb_array_elements(coalesce(to_jsonb(b)->'itinerary','[]'::jsonb)) part(value)
                    left join staff person on person.id=(part.value->>'staff_id')::uuid),'[]'::jsonb) as segments,
                  coalesce((to_jsonb(b)->>'is_multi_staff')::boolean,false) as is_multi_staff,
                  (b.status in ('confirmed','checked_in','completed') and b.payment_status='unpaid'
                    and s.is_active and s.profile_completed and s.approval_status='approved'
                    and exists(select 1 from profiles ap where ap.id=:actor_id and ap.is_active and ap.role in ('owner','staff'))
                    and (s.owner_id=:actor_id or exists(select 1 from staff collect_staff
                      where (collect_staff.id=b.staff_id or exists(select 1 from jsonb_array_elements(coalesce(to_jsonb(b)->'itinerary','[]'::jsonb)) collect_segment where (collect_segment->>'staff_id')::uuid=collect_staff.id)) and collect_staff.profile_id=:actor_id and collect_staff.is_active))) as can_record_payment,
                  coalesce((to_jsonb(b)->>'change_version')::integer,0) as change_version,
                  coalesce((to_jsonb(b)->>'committed_reschedules')::integer,0) as committed_reschedules,
                  (to_jsonb(b)->>'service_fulfilment_amount')::numeric as service_fulfilment_amount,
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
                left join booking_services bs on bs.booking_id = b.id and coalesce((to_jsonb(bs)->>'is_active')::boolean, true)
                where {' and '.join(filters)}
                group by b.id, s.name, s.owner_id, s.address, s.is_active, s.profile_completed, s.approval_status, img.url, st.name, st.photo_url
                order by b.start_datetime desc, b.id desc
                limit :limit offset :offset
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
                  b.total_duration_minutes, b.total_price, b.checkout_policy_version,
                  coalesce((select jsonb_agg(part.value || jsonb_build_object('staff_name',person.name) order by (part.value->>'ordinal')::int)
                    from jsonb_array_elements(coalesce(to_jsonb(b)->'itinerary','[]'::jsonb)) part(value)
                    left join staff person on person.id=(part.value->>'staff_id')::uuid),'[]'::jsonb) as segments,
                  coalesce((to_jsonb(b)->>'is_multi_staff')::boolean,false) as is_multi_staff,
                  (b.status in ('confirmed','checked_in','completed') and b.payment_status='unpaid'
                    and s.is_active and s.profile_completed and s.approval_status='approved'
                    and exists(select 1 from profiles ap where ap.id=:actor_id and ap.is_active and ap.role in ('owner','staff'))
                    and (s.owner_id=:actor_id or exists(select 1 from staff collect_staff
                      where (collect_staff.id=b.staff_id or exists(select 1 from jsonb_array_elements(coalesce(to_jsonb(b)->'itinerary','[]'::jsonb)) collect_segment where (collect_segment->>'staff_id')::uuid=collect_staff.id)) and collect_staff.profile_id=:actor_id and collect_staff.is_active))) as can_record_payment,
                  coalesce((to_jsonb(b)->>'change_version')::integer,0) as change_version,
                  coalesce((to_jsonb(b)->>'committed_reschedules')::integer,0) as committed_reschedules,
                  (to_jsonb(b)->>'service_fulfilment_amount')::numeric as service_fulfilment_amount,
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
                left join booking_services bs on bs.booking_id = b.id and coalesce((to_jsonb(bs)->>'is_active')::boolean, true)
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
                group by b.id, s.name, s.owner_id, s.address, s.is_active, s.profile_completed, s.approval_status, img.url, st.name, st.photo_url
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
