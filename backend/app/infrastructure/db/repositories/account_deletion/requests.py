"""Confirmation, request queue and closed-salon statement statements."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DeletionBlockedError, InvalidVerificationCodeError
from app.core.tokens import digests_match
from app.infrastructure.db.json_utils import decode_json
from app.infrastructure.db.repositories.account_deletion.constants import (
    _OWNED_SALONS,
    SHELL_SALON_NAME,
)
from app.infrastructure.db.repositories.payment_repository import _SETTLED


class _RequestMixin:
    session: AsyncSession

    async def confirm_deletion(
        self, user_id: str, challenge_id: str, confirmation_hash: str,
    ) -> dict[str, Any]:
        try:
            return await self._confirm(user_id, challenge_id, confirmation_hash)
        except BaseException:
            await self.session.rollback()
            raise

    async def _confirm(self, user_id: str, challenge_id: str, confirmation_hash: str) -> dict[str, Any]:
        s = self.session
        profile = (await s.execute(
            text("select id, role, is_active from profiles where id = :uid for update"),
            {"uid": user_id},
        )).mappings().one_or_none()
        challenge = (await s.execute(
            text("""
                select status, confirmation_hash, confirmation_expires_at > now() as fresh
                from account_deletion_challenges
                where id = :id and user_id = :uid for update
            """),
            {"id": challenge_id, "uid": user_id},
        )).mappings().one_or_none()
        hash_ok = challenge is not None and digests_match(
            challenge["confirmation_hash"], confirmation_hash
        )
        if profile is None or challenge is None or not hash_ok:
            raise InvalidVerificationCodeError("The confirmation is invalid or expired")

        if not profile["is_active"]:
            existing = (await s.execute(
                text("""
                    select id, status from account_deletion_requests
                    where user_id = :uid and status <> 'completed'
                """),
                {"uid": user_id},
            )).mappings().one_or_none()
            if existing is not None and challenge["status"] == "consumed":
                await s.rollback()
                return dict(existing)
            raise InvalidVerificationCodeError("The confirmation is invalid or expired")
        if challenge["status"] != "verified" or not challenge["fresh"]:
            raise InvalidVerificationCodeError("The confirmation is invalid or expired")

        role = str(profile["role"])
        salon = None
        staff_profile_ids: list[str] = []
        salon_ids: list[str] = []
        media_urls: list[str] = []
        avatar = (await s.execute(
            text("select avatar_url from profiles where id = :uid"), {"uid": user_id}
        )).scalar_one()
        if avatar:
            media_urls.append(avatar)
        if role == "owner":
            salon = (await s.execute(
                text("select id, name, city from salons where owner_id = :uid "
                     "order by created_at limit 1 for update"),
                {"uid": user_id},
            )).mappings().one_or_none()
            await s.execute(
                text("update salons set is_active = false where owner_id = :uid"),
                {"uid": user_id},
            )
            salon_ids = [
                str(r[0]) for r in (await s.execute(
                    text("select id from salons where owner_id = :uid order by created_at"),
                    {"uid": user_id},
                )).all()
            ]
            rows = await s.execute(
                text(f"""
                    select distinct st.profile_id from staff st
                    join profiles p on p.id = st.profile_id and p.role = 'staff'
                    where st.salon_id in ({_OWNED_SALONS})
                      and not exists (
                        select 1 from staff other
                        where other.profile_id = st.profile_id and other.is_active
                          and other.salon_id not in ({_OWNED_SALONS}))
                """),
                {"uid": user_id},
            )
            staff_profile_ids = [str(r[0]) for r in rows.all()]
            await s.execute(
                text(f"update staff set is_active = false where salon_id in ({_OWNED_SALONS})"),
                {"uid": user_id},
            )
            if staff_profile_ids:
                await s.execute(
                    text("update profiles set is_active = false where id = any(cast(:ids as uuid[]))"),
                    {"ids": staff_profile_ids},
                )
                avatars = await s.execute(
                    text("select avatar_url from profiles where id = any(cast(:ids as uuid[]))"),
                    {"ids": staff_profile_ids},
                )
                media_urls.extend(str(r[0]) for r in avatars.all() if r[0])
            urls = await s.execute(
                text(f"""
                    select url from salon_images where salon_id in ({_OWNED_SALONS})
                    union select photo_url from staff where salon_id in ({_OWNED_SALONS})
                    union select photo_url from services where salon_id in ({_OWNED_SALONS})
                    union select qr_image_url from salons where owner_id = :uid
                """),
                {"uid": user_id},
            )
            media_urls.extend(str(r[0]) for r in urls.all() if r[0])

        # Owners are never blocked by open bookings/requests: the worker cancels and
        # refunds them. Customers still resolve their own.
        blockers = await self.count_blockers(user_id, role)
        blocker_details: dict[str, int] = {}
        if blockers["open_bookings"]:
            blocker_details["open_bookings"] = blockers["open_bookings"]
        if blockers["pending_requests"]:
            blocker_details["pending_requests"] = blockers["pending_requests"]
        if blocker_details:
            raise DeletionBlockedError(
                "Cancel your upcoming bookings and resolve pending requests before "
                "deleting your account",
                details=blocker_details,
            )

        await s.execute(text("update profiles set is_active = false where id = :uid"),
                        {"uid": user_id})
        await s.execute(text("delete from device_tokens where user_id = :uid"), {"uid": user_id})
        await s.execute(text("delete from notifications where user_id = :uid"), {"uid": user_id})
        request = (await s.execute(
            text("""
                insert into account_deletion_requests
                  (user_id, role, salon_id, salon_name, salon_city, step_state, media_keys)
                values (:uid, :role, :salon_id, :salon_name, :salon_city,
                        cast(:state as jsonb), cast(:media as jsonb))
                returning id, status
            """),
            {"uid": user_id, "role": role,
             "salon_id": str(salon["id"]) if salon else None,
             "salon_name": salon["name"] if salon else None,
             "salon_city": salon["city"] if salon else None,
             "state": json.dumps(
                 {"staff_profile_ids": staff_profile_ids, "salon_ids": salon_ids}),
             "media": json.dumps(sorted(set(media_urls)))},
        )).mappings().one()
        await s.execute(
            text("update account_deletion_challenges set status = 'consumed', "
                 "consumed_at = now() where id = :id"),
            {"id": challenge_id},
        )
        await s.commit()
        return dict(request)

    async def get_request(self, request_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("""
                select id, status, requested_at, completed_at, step_state
                from account_deletion_requests
                where id = :id
            """),
            {"id": request_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        data = dict(row)
        data["step_state"] = decode_json(data["step_state"]) or {}
        return data

    async def list_requests(self, limit: int, offset: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text("""
                select id, role, salon_id, salon_name, salon_city, status,
                       requested_at, completed_at, attempts, last_error_code,
                       next_attempt_at, updated_at
                from account_deletion_requests
                order by requested_at desc limit :limit offset :offset
            """),
            {"limit": limit, "offset": offset},
        )
        return [dict(r) for r in result.mappings().all()]

    async def list_closed_salons(self, limit: int, offset: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text("""
                select id, role, salon_id, salon_name, salon_city, status,
                       requested_at, completed_at, attempts, last_error_code,
                       next_attempt_at, updated_at
                from account_deletion_requests
                where role = 'owner' and salon_id is not null
                order by requested_at desc limit :limit offset :offset
            """),
            {"limit": limit, "offset": offset},
        )
        return [dict(r) for r in result.mappings().all()]

    async def closed_salon_monthly_statement(self, salon_id: str) -> list[dict[str, Any]] | None:
        # Closed = named in an owner deletion request, or already an erased shell (this also
        # covers every salon of an owner who had more than one; the ledger names only the first).
        closed = (await self.session.execute(
            text("""
                select 1 from account_deletion_requests
                where role = 'owner' and salon_id = cast(:s as uuid)
                union all
                select 1 from salons
                where id = cast(:s as uuid) and owner_id is null and not is_active and name = :shell
                limit 1
            """),
            {"s": salon_id, "shell": SHELL_SALON_NAME},
        )).first()
        if closed is None:
            return None
        # Months follow the platform's business calendar (Asia/Kolkata), as the booking
        # trigger does for booking_calendar_date. Formulas mirror PaymentRepository.earnings.
        result = await self.session.execute(
            text(f"""
                with pay as (
                  select date_trunc('month', coalesce(p.captured_at, p.created_at)
                                    at time zone 'Asia/Kolkata')::date as month,
                         p.currency,
                         coalesce(sum(p.amount - p.overcollected_amount) filter (
                           where p.channel = 'gateway' and p.status in {_SETTLED}), 0) as online_collected,
                         coalesce(sum(p.platform_commission_amount) filter (
                           where p.channel = 'gateway' and p.status in {_SETTLED}), 0) as platform_fees,
                         coalesce(sum(p.overcollected_amount) filter (
                           where p.channel = 'gateway' and p.status in {_SETTLED}), 0) as overcollected,
                         coalesce(sum(p.amount) filter (where p.channel = 'manual'), 0) as manual_recorded,
                         count(*) filter (
                           where p.channel = 'gateway' and p.status in {_SETTLED}) as online_count,
                         count(*) filter (where p.channel = 'manual') as manual_count
                  from booking_payments p
                  where p.salon_id = cast(:s as uuid)
                    and (p.channel = 'manual' or p.status in {_SETTLED})
                  group by 1, 2
                ), ref as (
                  select date_trunc('month', coalesce(r.processed_at, r.created_at) at time zone 'Asia/Kolkata')::date as month,
                         p.currency,
                         coalesce(sum(r.amount) filter (where not r.applies_to_excess), 0) as online_refunded,
                         coalesce(sum(r.commission_reversal_amount), 0) as commission_reversed
                  from payment_refunds r join booking_payments p on p.id = r.payment_id
                  where p.salon_id = cast(:s as uuid) and r.status = 'processed'
                  group by 1, 2
                ), sub as (
                  select date_trunc('month', b.paid_at at time zone 'Asia/Kolkata')::date as month,
                         b.currency::text as currency,
                         coalesce(sum(b.amount), 0) as subscription_paid,
                         coalesce(sum(b.refunded_amount), 0) as subscription_refunded
                  from subscription_billing_records b
                  where b.salon_id = cast(:s as uuid) and b.paid_at is not null
                    and b.status in ('paid', 'refunded', 'partially_refunded')
                  group by 1, 2
                ), keys as (
                  select month, currency from pay
                  union select month, currency from ref
                  union select month, currency from sub
                )
                select k.month, k.currency,
                       coalesce(pay.online_collected, 0) as online_collected,
                       coalesce(pay.platform_fees, 0) as platform_fees,
                       coalesce(pay.overcollected, 0) as overcollected,
                       coalesce(pay.manual_recorded, 0) as manual_recorded,
                       coalesce(pay.online_count, 0) as online_count,
                       coalesce(pay.manual_count, 0) as manual_count,
                       coalesce(ref.online_refunded, 0) as online_refunded,
                       coalesce(ref.commission_reversed, 0) as commission_reversed,
                       coalesce(sub.subscription_paid, 0) as subscription_paid,
                       coalesce(sub.subscription_refunded, 0) as subscription_refunded
                from keys k
                left join pay on pay.month = k.month and pay.currency = k.currency
                left join ref on ref.month = k.month and ref.currency = k.currency
                left join sub on sub.month = k.month and sub.currency = k.currency
                order by k.month, k.currency
            """),
            {"s": salon_id},
        )
        return [dict(r) for r in result.mappings().all()]

    async def claim_due_request(self, stale_seconds: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("""
                update account_deletion_requests
                set status = 'processing', attempts = attempts + 1, updated_at = now()
                where id = (
                  select id from account_deletion_requests
                  where user_id is not null and (
                        (status in ('pending', 'failed') and next_attempt_at <= now())
                     or (status = 'processing'
                         and updated_at < now() - :stale * interval '1 second'))
                  order by next_attempt_at limit 1 for update skip locked
                )
                returning id, user_id, role, salon_id, step_state, media_keys, attempts
            """),
            {"stale": stale_seconds},
        )
        row = result.mappings().one_or_none()
        await self.session.commit()
        if row is None:
            return None
        data = dict(row)
        data["step_state"] = decode_json(data["step_state"]) or {}
        data["media_keys"] = decode_json(data["media_keys"]) or []
        return data

    async def record_step(self, request_id: str, step: str) -> None:
        await self.session.execute(
            text("""
                update account_deletion_requests
                set step_state = step_state || cast(:patch as jsonb), updated_at = now()
                where id = :id and status = 'processing'
            """),
            {"id": request_id, "patch": json.dumps({step: True})},
        )
        await self.session.commit()

    async def fail_request(self, request_id: str, error_code: str, delay_seconds: int) -> None:
        await self.session.rollback()
        await self.session.execute(
            text("""
                update account_deletion_requests
                set status = 'failed', last_error_code = :code, updated_at = now(),
                    next_attempt_at = now() + :delay * interval '1 second'
                where id = :id and status = 'processing'
            """),
            {"id": request_id, "code": error_code[:80], "delay": delay_seconds},
        )
        await self.session.commit()

    async def requeue_request(self, request_id: str, reason_code: str, delay_seconds: int) -> None:
        """Wait without failing: used while refunds settle, so the status stays ``pending``."""

        await self.session.rollback()
        await self.session.execute(
            text("""
                update account_deletion_requests
                set status = 'pending', last_error_code = :code, updated_at = now(),
                    next_attempt_at = now() + :delay * interval '1 second'
                where id = :id and status = 'processing'
            """),
            {"id": request_id, "code": reason_code[:80], "delay": delay_seconds},
        )
        await self.session.commit()

    async def complete_request(self, request_id: str) -> None:
        """Close the ledger row: drop every identifier and anonymise the salon snapshot."""

        await self.session.execute(
            text("""
                update account_deletion_requests
                set status = 'completed', completed_at = now(), updated_at = now(),
                    user_id = null, media_keys = '[]'::jsonb, last_error_code = null,
                    step_state = '{}'::jsonb,
                    salon_name = case when salon_name is null then null else :shell end,
                    salon_city = null
                where id = :id and status = 'processing'
            """),
            {"id": request_id, "shell": SHELL_SALON_NAME},
        )
        await self.session.commit()
