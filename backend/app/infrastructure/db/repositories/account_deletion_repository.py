"""SQL adapter for account-deletion challenges, ledger and erasure."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.account_deletion_repository import AccountDeletionRepository
from app.core.exceptions import DeletionBlockedError, InvalidVerificationCodeError, NotFoundError
from app.core.tokens import digests_match

_CHALLENGE_COLUMNS = (
    "id, user_id, channel, contact_hash, status, attempts, max_attempts, resend_count, "
    "last_sent_at, expires_at, confirmation_hash, "
    "extract(epoch from (now() - last_sent_at)) as seconds_since_sent"
)
_OWNED_SALONS = "select id from salons where owner_id = :uid"


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


class SQLAccountDeletionRepository(AccountDeletionRepository):
    """Every method commits (or rolls back) its own unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_blockers(self, user_id: str, role: str) -> dict[str, int]:
        if role == "owner":
            bookings = f"""
                select count(*) from bookings b
                where b.salon_id in ({_OWNED_SALONS})
                  and b.status in ('pending', 'confirmed') and b.end_datetime > now()"""
            requests = f"""
                select count(*) from booking_action_requests r
                join bookings b on b.id = r.booking_id
                where b.salon_id in ({_OWNED_SALONS}) and r.status = 'pending'"""
            subscriptions = f"""
                select count(*) from salon_subscriptions
                where salon_id in ({_OWNED_SALONS})
                  and status in ('active', 'trialing', 'past_due')"""
        else:
            bookings = """
                select count(*) from bookings b
                where b.customer_id = :uid
                  and b.status in ('pending', 'confirmed') and b.end_datetime > now()"""
            requests = """
                select count(*) from booking_action_requests r
                where r.requested_by = :uid and r.status = 'pending'"""
            subscriptions = "select 0"
        counts: dict[str, int] = {}
        for name, sql in (
            ("open_bookings", bookings),
            ("pending_requests", requests),
            ("active_subscriptions", subscriptions),
        ):
            result = await self.session.execute(text(sql), {"uid": user_id})
            counts[name] = int(result.scalar_one())
        return counts

    async def count_recent_challenges(self, user_id: str, window_seconds: int) -> int:
        result = await self.session.execute(
            text("""
                select count(*) from account_deletion_challenges
                where user_id = :uid and created_at > now() - :w * interval '1 second'
            """),
            {"uid": user_id, "w": window_seconds},
        )
        return int(result.scalar_one())

    async def get_live_challenge(self, user_id: str) -> dict[str, Any] | None:
        await self.session.execute(
            text("""
                update account_deletion_challenges set status = 'expired'
                where user_id = :uid and (
                  (status = 'sent' and expires_at <= now()) or
                  (status = 'verified' and confirmation_expires_at <= now())
                )
            """),
            {"uid": user_id},
        )
        result = await self.session.execute(
            text(f"""
                select {_CHALLENGE_COLUMNS} from account_deletion_challenges
                where user_id = :uid and status in ('sent', 'verified')
            """),
            {"uid": user_id},
        )
        row = result.mappings().one_or_none()
        await self.session.commit()
        return dict(row) if row else None

    async def expire_live_challenge(self, user_id: str) -> None:
        await self.session.execute(
            text("""
                update account_deletion_challenges set status = 'expired'
                where user_id = :uid and status in ('sent', 'verified')
            """),
            {"uid": user_id},
        )
        await self.session.commit()

    async def create_challenge(
        self, user_id: str, channel: str, contact_hash: str, ttl_seconds: int, max_attempts: int,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(f"""
                insert into account_deletion_challenges
                  (user_id, channel, contact_hash, expires_at, max_attempts)
                values (:uid, :channel, :hash, now() + :ttl * interval '1 second', :max_attempts)
                returning {_CHALLENGE_COLUMNS}
            """),
            {"uid": user_id, "channel": channel, "hash": contact_hash,
             "ttl": ttl_seconds, "max_attempts": max_attempts},
        )
        row = dict(result.mappings().one())
        await self.session.commit()
        return row

    async def resend_challenge(
        self, challenge_id: str, channel: str, contact_hash: str, ttl_seconds: int,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(f"""
                update account_deletion_challenges
                set channel = :channel, contact_hash = :hash, resend_count = resend_count + 1,
                    last_sent_at = now(), expires_at = now() + :ttl * interval '1 second'
                where id = :id and status = 'sent'
                returning {_CHALLENGE_COLUMNS}
            """),
            {"id": challenge_id, "channel": channel, "hash": contact_hash, "ttl": ttl_seconds},
        )
        row = result.mappings().one_or_none()
        await self.session.commit()
        if row is None:
            raise NotFoundError("Verification challenge not found")
        return dict(row)

    async def get_challenge(self, challenge_id: str, user_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(f"""
                select {_CHALLENGE_COLUMNS} from account_deletion_challenges
                where id = :id and user_id = :uid
            """),
            {"id": challenge_id, "uid": user_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def begin_verify_attempt(self, challenge_id: str, user_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(f"""
                update account_deletion_challenges set attempts = attempts + 1
                where id = :id and user_id = :uid and status = 'sent'
                  and expires_at > now() and attempts < max_attempts
                returning {_CHALLENGE_COLUMNS}
            """),
            {"id": challenge_id, "uid": user_id},
        )
        row = result.mappings().one_or_none()
        await self.session.commit()
        return dict(row) if row else None

    async def expire_challenge(self, challenge_id: str) -> None:
        await self.session.execute(
            text("""
                update account_deletion_challenges set status = 'expired'
                where id = :id and status = 'sent'
            """),
            {"id": challenge_id},
        )
        await self.session.commit()

    async def mark_verified(
        self, challenge_id: str, user_id: str, confirmation_hash: str, ttl_seconds: int,
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("""
                update account_deletion_challenges
                set status = 'verified', verified_at = now(), confirmation_hash = :hash,
                    confirmation_expires_at = now() + :ttl * interval '1 second'
                where id = :id and user_id = :uid and status = 'sent' and expires_at > now()
                returning id, confirmation_expires_at
            """),
            {"id": challenge_id, "uid": user_id, "hash": confirmation_hash, "ttl": ttl_seconds},
        )
        row = result.mappings().one_or_none()
        await self.session.commit()
        return dict(row) if row else None

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

        blockers = await self.count_blockers(user_id, role)
        blocker_details: dict[str, int] = {}
        if blockers["open_bookings"]:
            blocker_details["open_bookings"] = blockers["open_bookings"]
        if blockers["pending_requests"]:
            blocker_details["pending_requests"] = blockers["pending_requests"]
        if blocker_details:
            raise DeletionBlockedError(
                "Resolve open bookings and pending requests before deleting your account",
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
             "state": json.dumps({"staff_profile_ids": staff_profile_ids}),
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
                select id, status, requested_at, completed_at from account_deletion_requests
                where id = :id
            """),
            {"id": request_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def list_requests(self, limit: int, offset: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text("""
                select id, role, salon_id, salon_name, salon_city, status,
                       requested_at, completed_at
                from account_deletion_requests
                order by requested_at desc limit :limit offset :offset
            """),
            {"limit": limit, "offset": offset},
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
        data["step_state"] = _json(data["step_state"]) or {}
        data["media_keys"] = _json(data["media_keys"]) or []
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

    async def complete_request(self, request_id: str) -> None:
        await self.session.execute(
            text("""
                update account_deletion_requests
                set status = 'completed', completed_at = now(), updated_at = now(),
                    user_id = null, media_keys = '[]'::jsonb, last_error_code = null
                where id = :id and status = 'processing'
            """),
            {"id": request_id},
        )
        await self.session.commit()

    async def erase_database(self, user_id: str, role: str) -> None:
        s = self.session
        try:
            await s.execute(text("select set_config('app.account_erasure', 'on', true)"))
            params = {"uid": user_id}
            await s.execute(text("delete from notifications where user_id = :uid"), params)
            await s.execute(text("delete from device_tokens where user_id = :uid"), params)
            await s.execute(text("delete from salon_reports where reporter_id = :uid"), params)
            await s.execute(
                text("update booking_action_requests set reason = null where requested_by = :uid"),
                params,
            )
            await s.execute(
                text("""
                    update bookings
                    set customer_name = 'Deleted customer', customer_phone = null, notes = null
                    where customer_id = :uid
                """),
                params,
            )
            if role == "owner":
                await self._scrub_owner_business(params)
            await s.execute(text("select erase_profile_references(:uid)"), params)
            await s.execute(text("delete from profiles where id = :uid"), params)
            await s.commit()
        except BaseException:
            await s.rollback()
            raise

    async def _scrub_owner_business(self, params: dict[str, str]) -> None:
        s = self.session
        await s.execute(
            text("""
                update salons
                set is_active = false, description = null, address = null, lat = null,
                    lng = null, qr_image_url = null, working_hours = '{}'::jsonb,
                    qr_token = encode(gen_random_bytes(16), 'hex')
                where owner_id = :uid
            """),
            params,
        )
        await s.execute(
            text(f"delete from salon_images where salon_id in ({_OWNED_SALONS})"), params
        )
        await s.execute(
            text(f"update services set photo_url = null where salon_id in ({_OWNED_SALONS})"),
            params,
        )
        await s.execute(
            text(f"""
                delete from blocked_slots
                where salon_id in ({_OWNED_SALONS})
                   or staff_id in (select id from staff where salon_id in ({_OWNED_SALONS}))
            """),
            params,
        )
        await s.execute(
            text(f"""
                update staff
                set name = 'Former staff', photo_url = null, specialization = null,
                    profile_id = null, is_active = false
                where salon_id in ({_OWNED_SALONS})
            """),
            params,
        )

    async def profile_exists(self, user_id: str) -> bool:
        result = await self.session.execute(
            text("select exists (select 1 from profiles where id = :uid)"), {"uid": user_id}
        )
        return bool(result.scalar_one())
