"""Admin insights repository — read-only queries over salons, subscriptions and bookings.

Nothing here changes data except ``bulk_set_plan_price``, which applies one offer to many salons
in a single transaction.
"""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SETTLED = "('captured', 'partially_refunded', 'refunded')"

# One row per approved, active salon with its subscription state. The rules mirror
# public.salon_booking_eligible (paid access, or an open trial) plus the past_due grace window.
#   paid_access : ANY active/cancelled subscription whose paid period covers now (as the function does)
#   in_grace    : the latest subscription is past_due and still inside its grace period. The function
#                 does not let such a salon book, so it is shown under "ending soon" until grace ends.
#   in_trial    : the free trial is running and its booking limit is not reached
# For display and for the lapsed/none split, the latest NON-pending subscription decides:
# a pending row never granted access.
_CLASSIFIED = """
    with base as (
      select s.id as salon_id, s.name as salon_name, s.city, s.approval_status, s.approved_at,
             p.full_name as owner_name, p.email as owner_email, p.phone as owner_phone,
             ls.status::text as subscription_status, ls.plan_code, ls.plan_name,
             ls.current_period_end, ls.grace_period_end, ls.cancelled_at,
             a.trial_ends_at, a.bookings_counted as trial_bookings_counted,
             a.trial_booking_limit, a.trial_ended_reason,
             pd.paid_until, (pd.paid_until is not null) as paid_access,
             coalesce(ls.status = 'past_due' and ls.grace_period_end > now(), false) as in_grace,
             coalesce(a.trial_started_at <= now() and a.trial_ends_at > now()
                      and a.trial_limit_reached_at is null
                      and a.bookings_counted < a.trial_booking_limit, false) as in_trial
      from salons s
      join profiles p on p.id = s.owner_id
      left join lateral (
        select ss.status, ss.current_period_start, ss.current_period_end,
               ss.grace_period_end, ss.cancelled_at, pl.code as plan_code, pl.name as plan_name
        from salon_subscriptions ss
        join subscription_plans pl on pl.id = ss.plan_id
        where ss.salon_id = s.id and ss.status <> 'pending'
        order by ss.created_at desc, ss.id desc
        limit 1
      ) ls on true
      left join lateral (
        select max(pa.current_period_end) as paid_until
        from salon_subscriptions pa
        where pa.salon_id = s.id and pa.status in ('active', 'cancelled')
          and pa.current_period_start <= now() and pa.current_period_end > now()
      ) pd on true
      left join salon_access a on a.salon_id = s.id
      where s.is_active and s.approval_status = 'approved'
        and (cast(:search as text) is null or s.name ilike :search
             or p.email ilike :search or s.city ilike :search)
    ), classified as (
      select b.*,
             case
               when paid_access
                    and paid_until <= now() + make_interval(days => cast(:within as int))
                 then 'ending_soon'
               when in_trial and not paid_access and not in_grace
                    and trial_ends_at <= now() + make_interval(days => cast(:within as int))
                 then 'ending_soon'
               when in_grace and not paid_access
                    and grace_period_end <= now() + make_interval(days => cast(:within as int))
                 then 'ending_soon'
               when paid_access or in_trial or in_grace then 'ok'
               when subscription_status is null then 'none'
               else 'lapsed'
             end as state,
             case
               when paid_access then paid_until
               when in_trial then trial_ends_at
               when subscription_status = 'past_due' then coalesce(grace_period_end, current_period_end)
               else coalesce(current_period_end, trial_ends_at, cancelled_at)
             end as ends_at
      from base b
    )
"""


class AdminInsightsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Subscription attention queue ─────────────────────────────────────────
    async def list_salon_subscriptions(
        self,
        *,
        state: str | None,
        within_days: int,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                _CLASSIFIED
                + """
                select c.*,
                       case when state in ('lapsed', 'none') and ends_at is not null
                            then greatest(0, floor(extract(epoch from (now() - ends_at)) / 86400))::int
                       end as days_since_end,
                       case when state = 'ending_soon' and ends_at is not null
                            then greatest(0, ceil(extract(epoch from (ends_at - now())) / 86400))::int
                       end as days_until_end
                from classified c
                where (cast(:state as text) is null and state <> 'ok') or state = cast(:state as text)
                order by case when state = 'ending_soon' then ends_at end asc nulls last,
                         case when state <> 'ending_soon' then ends_at end desc nulls last,
                         salon_name asc, salon_id asc
                limit :limit offset :offset
                """
            ),
            {
                "state": state,
                "within": within_days,
                "search": f"%{search}%" if search else None,
                "limit": limit,
                "offset": offset,
            },
        )
        return [dict(r) for r in result.mappings().all()]

    async def subscription_summary(self, *, within_days: int) -> dict[str, int]:
        result = await self.session.execute(
            text(
                _CLASSIFIED
                + """
                select count(*) filter (where state = 'lapsed') as lapsed,
                       count(*) filter (where state = 'none') as none,
                       count(*) filter (where state = 'ending_soon') as ending_soon
                from classified
                """
            ),
            {"within": within_days, "search": None},
        )
        row = result.mappings().one()
        return {k: int(row[k]) for k in ("lapsed", "none", "ending_soon")}

    # ── Per-salon analytics ──────────────────────────────────────────────────
    async def salon_header(self, salon_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("select id, name, approved_at from salons where id = cast(:s as uuid)"),
            {"s": salon_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def booking_counts(
        self, salon_id: str, date_from: date, date_to: date
    ) -> list[dict[str, Any]]:
        """Totals (``is_total = 1``) and one row per booking source."""

        result = await self.session.execute(
            text(
                """
                select b.source::text as source, grouping(b.source) as is_total,
                       count(*) as total,
                       count(*) filter (where b.status = 'pending') as pending,
                       count(*) filter (where b.status = 'confirmed') as confirmed,
                       count(*) filter (where b.status = 'checked_in') as checked_in,
                       count(*) filter (where b.status = 'completed') as completed,
                       count(*) filter (where b.status = 'cancelled') as cancelled,
                       count(*) filter (where b.status = 'rejected') as rejected,
                       count(*) filter (where b.status = 'no_show') as no_show,
                       count(distinct coalesce(b.customer_id::text, nullif(b.customer_phone, '')))
                         as customers,
                       coalesce(sum(b.total_price) filter (where b.status = 'completed'), 0)
                         as completed_value
                from bookings b
                where b.salon_id = cast(:s as uuid)
                  and b.booking_calendar_date between cast(:d_from as date) and cast(:d_to as date)
                group by grouping sets ((), (b.source))
                """
            ),
            {"s": salon_id, "d_from": date_from, "d_to": date_to},
        )
        return [dict(r) for r in result.mappings().all()]

    async def monthly_bookings(
        self, salon_id: str, date_from: date, date_to: date
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                select date_trunc('month', b.booking_calendar_date)::date as month,
                       count(*) as total,
                       count(*) filter (where b.status = 'completed') as completed,
                       count(*) filter (where b.status = 'cancelled') as cancelled,
                       count(*) filter (where b.status = 'no_show') as no_show
                from bookings b
                where b.salon_id = cast(:s as uuid)
                  and b.booking_calendar_date between cast(:d_from as date) and cast(:d_to as date)
                group by 1 order by 1
                """
            ),
            {"s": salon_id, "d_from": date_from, "d_to": date_to},
        )
        return [dict(r) for r in result.mappings().all()]

    async def monthly_money(
        self, salon_id: str, date_from: date, date_to: date
    ) -> list[dict[str, Any]]:
        """Ledger totals per month and currency. Formulas mirror PaymentRepository.earnings;
        months follow the platform's business calendar (Asia/Kolkata)."""

        result = await self.session.execute(
            text(
                f"""
                with pay as (
                  select date_trunc('month', coalesce(p.captured_at, p.created_at)
                                    at time zone 'Asia/Kolkata')::date as month,
                         p.currency,
                         coalesce(sum(p.amount - p.overcollected_amount) filter (
                           where p.channel = 'gateway' and p.status in {_SETTLED}), 0) as online_collected,
                         coalesce(sum(p.platform_commission_amount) filter (
                           where p.channel = 'gateway' and p.status in {_SETTLED}), 0) as platform_fees,
                         coalesce(sum(p.amount) filter (where p.channel = 'manual'), 0) as manual_recorded,
                         count(*) filter (
                           where p.channel = 'gateway' and p.status in {_SETTLED}) as online_count,
                         count(*) filter (where p.channel = 'manual') as manual_count
                  from booking_payments p
                  where p.salon_id = cast(:s as uuid)
                    and (p.channel = 'manual' or p.status in {_SETTLED})
                    and (coalesce(p.captured_at, p.created_at) at time zone 'Asia/Kolkata')::date
                        between cast(:d_from as date) and cast(:d_to as date)
                  group by 1, 2
                ), ref as (
                  select date_trunc('month', coalesce(r.processed_at, r.created_at)
                                    at time zone 'Asia/Kolkata')::date as month,
                         p.currency,
                         coalesce(sum(r.amount) filter (where not r.applies_to_excess), 0) as online_refunded,
                         coalesce(sum(r.commission_reversal_amount), 0) as commission_reversed
                  from payment_refunds r join booking_payments p on p.id = r.payment_id
                  where p.salon_id = cast(:s as uuid) and r.status = 'processed'
                    and (coalesce(r.processed_at, r.created_at) at time zone 'Asia/Kolkata')::date
                        between cast(:d_from as date) and cast(:d_to as date)
                  group by 1, 2
                ), sub as (
                  select date_trunc('month', b.paid_at at time zone 'Asia/Kolkata')::date as month,
                         b.currency::text as currency,
                         coalesce(sum(b.amount), 0) as subscription_paid
                  from subscription_billing_records b
                  where b.salon_id = cast(:s as uuid) and b.paid_at is not null
                    and b.status in ('paid', 'refunded', 'partially_refunded')
                    and (b.paid_at at time zone 'Asia/Kolkata')::date
                        between cast(:d_from as date) and cast(:d_to as date)
                  group by 1, 2
                ), keys as (
                  select month, currency from pay
                  union select month, currency from ref
                  union select month, currency from sub
                )
                select k.month, k.currency,
                       coalesce(pay.online_collected, 0) as online_collected,
                       coalesce(ref.online_refunded, 0) as online_refunded,
                       coalesce(pay.platform_fees, 0) - coalesce(ref.commission_reversed, 0)
                         as platform_commission_net,
                       coalesce(pay.manual_recorded, 0) as manual_recorded,
                       coalesce(sub.subscription_paid, 0) as subscription_paid,
                       coalesce(pay.online_count, 0) as online_payment_count,
                       coalesce(pay.manual_count, 0) as manual_payment_count
                from keys k
                left join pay on pay.month = k.month and pay.currency = k.currency
                left join ref on ref.month = k.month and ref.currency = k.currency
                left join sub on sub.month = k.month and sub.currency = k.currency
                order by k.month, k.currency
                """
            ),
            {"s": salon_id, "d_from": date_from, "d_to": date_to},
        )
        return [dict(r) for r in result.mappings().all()]

    # ── Bulk offer ───────────────────────────────────────────────────────────
    async def find_missing_salons(self, salon_ids: list[str]) -> list[str]:
        result = await self.session.execute(
            text("select id::text from salons where id = any(cast(:ids as uuid[]))"),
            {"ids": salon_ids},
        )
        found = {r[0] for r in result.all()}
        return [s for s in salon_ids if s not in found]

    async def bulk_set_plan_price(
        self,
        salon_ids: list[str],
        plan_id: str,
        price: Decimal,
        actor_id: str,
        valid_until: datetime | None,
    ) -> int:
        """Upsert one offer for every salon and audit each, in ONE transaction: all or nothing."""

        await self.session.execute(
            text(
                """
                insert into salon_plan_prices (salon_id, plan_id, price_amount, set_by, valid_until)
                select s, cast(:plan as uuid), cast(:price as numeric), cast(:actor as uuid),
                       cast(:until as timestamptz)
                from unnest(cast(:ids as uuid[])) as s
                on conflict (salon_id, plan_id) do update
                  set price_amount = excluded.price_amount, set_by = excluded.set_by,
                      valid_until = excluded.valid_until, updated_at = now()
                """
            ),
            {"ids": salon_ids, "plan": plan_id, "price": price, "actor": actor_id, "until": valid_until},
        )
        events = [
            {
                "ref": f"plan-price:{uuid4()}",
                "hash": hashlib.sha256(
                    json.dumps(
                        {"salon": sid, "plan": plan_id, "price": str(price), "actor": actor_id},
                        sort_keys=True,
                    ).encode()
                ).hexdigest(),
            }
            for sid in salon_ids
        ]
        await self.session.execute(
            text(
                """
                insert into subscription_events
                  (provider_name, provider_event_reference, event_type, payload_hash,
                   processing_status, processed_at)
                values ('admin', :ref, 'admin_plan_price_set', :hash, 'processed', now())
                """
            ),
            events,
        )
        await self.session.commit()
        return len(salon_ids)
