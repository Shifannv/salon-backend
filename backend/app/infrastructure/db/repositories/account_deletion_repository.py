"""SQL adapter for account-deletion challenges, ledger and erasure."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.account_deletion_repository import AccountDeletionRepository
from app.core.exceptions import DeletionBlockedError, InvalidVerificationCodeError, NotFoundError
from app.core.tokens import digests_match
from app.infrastructure.account_deletion.privacy import (
    authored_quote_pattern,
    personal_text_pattern,
    quoted_text_pattern,
)
from app.infrastructure.db.json_utils import decode_json
from app.infrastructure.db.repositories.payment_repository import _SETTLED
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)

_CHALLENGE_COLUMNS = (
    "id, user_id, channel, contact_hash, status, attempts, max_attempts, resend_count, "
    "last_sent_at, expires_at, confirmation_hash, "
    "extract(epoch from (now() - last_sent_at)) as seconds_since_sent"
)
_OWNED_SALONS = "select id from salons where owner_id = :uid"

# Salons are soft-deactivated, never deleted, so ``on delete cascade`` foreign keys to
# salons(id) NEVER fire. Every such table must be emptied explicitly by
# ``_scrub_owner_business``. tests/unit/test_account_erasure_schema_guard.py fails when a
# migration adds a cascade FK to salons that is missing from this tuple.
SALON_CASCADE_TABLES: tuple[str, ...] = (
    "salon_images",
    "salon_holidays",
    "blocked_slots",
    "salon_payout_accounts",
    "salon_payout_account_history",
    "salon_access",
)
# Plain (NO ACTION) salon references that hold provider-side identifiers: also emptied.
SALON_PROVIDER_REFERENCE_TABLES: tuple[str, ...] = (
    "subscription_provider_accounts",
    "payment_provider_accounts",
)

SALON_CLOSED_REASON = "salon_closed"
CLOSURE_REFUND_KEY = "salon_closed"
SHELL_SALON_NAME = "Closed salon"
REMOVED_TEXT = "Removed"
ANONYMISED_NOTIFICATION_TITLE = "Booking update"

CLOSURE_NOTICE_BASE = "This salon has closed, so your booking has been cancelled."
CLOSURE_NOTICE_ONLINE = " Any online payment you made will be refunded to your original payment method."
CLOSURE_NOTICE_MANUAL = (
    " A payment you made directly to the salon is not refunded by the platform."
)


class SQLAccountDeletionRepository(AccountDeletionRepository):
    """Every method commits (or rolls back) its own unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_blockers(self, user_id: str, role: str) -> dict[str, int]:
        """Counts that genuinely block deletion.

        An owner's open bookings and pending requests are NOT blockers: the worker
        cancels, notifies and refunds them (``count_closure_impact``). Only an active
        subscription can block an owner. A customer still has to resolve their own
        upcoming bookings and pending requests.
        """

        if role == "owner":
            bookings = requests = "select 0"
            subscriptions = f"""
                select count(*) from salon_subscriptions
                where salon_id in ({_OWNED_SALONS})
                  and status in ('active', 'trialing', 'past_due')"""
        else:
            bookings = """
                select count(*) from bookings b
                where b.customer_id = :uid
                  and ((b.status in ('pending', 'confirmed') and b.end_datetime > now())
                       or b.status = 'checked_in')"""
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

    async def count_closure_impact(self, user_id: str) -> dict[str, int]:
        """What closing an owner's salons will do: bookings cancelled, requests resolved."""

        result = await self.session.execute(
            text(f"""
                select
                  (select count(*) from bookings b
                    where b.salon_id in ({_OWNED_SALONS})
                      and b.status in ('pending', 'confirmed') and b.end_datetime > now()),
                  (select count(*) from booking_action_requests r
                    join bookings b on b.id = r.booking_id
                    where b.salon_id in ({_OWNED_SALONS}) and r.status = 'pending')
            """),
            {"uid": user_id},
        )
        bookings, requests = result.one()
        return {"bookings_to_cancel": int(bookings), "requests_to_resolve": int(requests)}

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

    # ------------------------------------------------------- cancel and refund
    async def cancel_open_bookings(self, user_id: str) -> dict[str, int]:
        """Cancel every future pending/confirmed booking at the owner's salons and tell
        each customer, in ONE transaction, so a retry can neither skip nor repeat a notice.

        Also resolves every open booking-action request at those salons and cancels
        never-attempted checkout intents. Returns counts; a re-run finds nothing to do.
        """

        s = self.session
        params = {"uid": user_id}
        try:
            # Same transaction: stop future subscription renewal, expire unpaid subscription
            # orders locally and flag paid-but-unused periods BEFORE anything is erased.
            await SubscriptionBillingRepository(s).wind_down_salons(user_id)
            rows = (await s.execute(
                text(f"""
                    select id from bookings
                    where salon_id in ({_OWNED_SALONS})
                      and status in ('pending', 'confirmed') and end_datetime > now()
                    order by id for update
                """),
                params,
            )).all()
            ids = [str(r[0]) for r in rows]
            notified = 0
            if ids:
                await s.execute(
                    text("""
                        update bookings
                        set status = 'cancelled', cancellation_reason = :reason
                        where id = any(cast(:ids as uuid[]))
                    """),
                    {"ids": ids, "reason": SALON_CLOSED_REASON},
                )
                await s.execute(
                    text("""
                        update booking_payments set status = 'cancelled'
                        where booking_id = any(cast(:ids as uuid[]))
                          and channel = 'gateway' and status = 'created'
                    """),
                    {"ids": ids},
                )
                notified = (await s.execute(
                    text("""
                        with created as (
                          insert into notifications (user_id, booking_id, type, title, body, data)
                          select b.customer_id, b.id, 'booking_cancelled', 'Booking cancelled',
                                 cast(:base as text)
                                 || case when exists (
                                      select 1 from booking_payments p
                                      where p.booking_id = b.id and p.channel = 'gateway'
                                        and p.status in ('captured', 'partially_refunded'))
                                    then cast(:online as text) else '' end
                                 || case when exists (
                                      select 1 from booking_payments p
                                      where p.booking_id = b.id and p.channel = 'manual'
                                        and p.status = 'captured' and p.amount > 0)
                                    then cast(:manual as text) else '' end,
                                 jsonb_build_object('reason', cast(:reason as text))
                          from bookings b
                          where b.id = any(cast(:ids as uuid[])) and b.customer_id is not null
                          returning id, user_id
                        ), queued as (
                          insert into notification_outbox (notification_id, user_id)
                          select id, user_id from created
                          returning 1
                        )
                        select count(*) from queued
                    """),
                    {"ids": ids, "base": CLOSURE_NOTICE_BASE, "online": CLOSURE_NOTICE_ONLINE,
                     "manual": CLOSURE_NOTICE_MANUAL, "reason": SALON_CLOSED_REASON},
                )).scalar_one()
            resolved = (await s.execute(
                text(f"""
                    update booking_action_requests
                    set status = 'resolved', decision = 'invalidated',
                        decision_reason = 'Salon closed', resolved_at = now()
                    where status = 'pending'
                      and booking_id in (select id from bookings where salon_id in ({_OWNED_SALONS}))
                """),
                params,
            )).rowcount
            await s.commit()
            return {"cancelled": len(ids), "notified": int(notified), "resolved": int(resolved or 0)}
        except BaseException:
            await s.rollback()
            raise

    async def list_closure_refund_candidates(self, user_id: str) -> list[dict[str, Any]]:
        """Online payments on closure-cancelled bookings, with any refund already begun."""

        result = await self.session.execute(
            text(f"""
                select p.id as payment_id, p.booking_id, p.provider, p.payment_ref, p.amount,
                       p.status as payment_status,
                       coalesce((select sum(r.amount) from payment_refunds r
                                 where r.payment_id = p.id and r.status <> 'failed'
                                   and r.idempotency_key <> :key), 0) as other_refunded,
                       c.id as refund_id, c.status as refund_status, c.refund_ref
                from booking_payments p
                join bookings b on b.id = p.booking_id
                left join payment_refunds c
                  on c.payment_id = p.id and c.idempotency_key = :key
                where b.salon_id in ({_OWNED_SALONS})
                  and b.status = 'cancelled' and b.cancellation_reason = :reason
                  and p.channel = 'gateway' and p.payment_ref is not null
                  and (p.status in ('captured', 'partially_refunded') or c.id is not null)
                order by p.created_at, p.id
            """),
            {"uid": user_id, "key": CLOSURE_REFUND_KEY, "reason": SALON_CLOSED_REASON},
        )
        return [dict(r) for r in result.mappings().all()]

    async def begin_closure_refund(
        self, payment_id: str, booking_id: str, provider: str | None, amount: Any
    ) -> dict[str, Any]:
        """Insert the refund row (or return the existing one) BEFORE calling the provider.

        ``unique (payment_id, idempotency_key)`` makes this exactly-once per payment.
        """

        s = self.session
        try:
            await s.execute(
                text("""
                    insert into payment_refunds
                      (payment_id, booking_id, provider, amount, status, reason, idempotency_key)
                    values (:p, :b, :provider, :amount, 'created', :reason, :key)
                    on conflict (payment_id, idempotency_key) do nothing
                """),
                {"p": payment_id, "b": booking_id, "provider": provider, "amount": amount,
                 "reason": SALON_CLOSED_REASON, "key": CLOSURE_REFUND_KEY},
            )
            row = (await s.execute(
                text("""
                    select id, status, refund_ref, amount from payment_refunds
                    where payment_id = :p and idempotency_key = :key
                """),
                {"p": payment_id, "key": CLOSURE_REFUND_KEY},
            )).mappings().one()
            await s.commit()
            return dict(row)
        except BaseException:
            await s.rollback()
            raise

    async def finish_closure_refund(
        self, refund_id: str, refund_ref: str | None, status: str, failure_code: str | None
    ) -> None:
        try:
            await self.session.execute(
                text("""
                    update payment_refunds
                    set refund_ref = :ref, status = :status, failure_code = :code,
                        processed_at = case when :status = 'processed' then now() else processed_at end
                    where id = :id and status = 'created'
                """),
                {"id": refund_id, "ref": refund_ref, "status": status,
                 "code": failure_code[:120] if failure_code else None},
            )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise

    async def record_failed_closure_refund(
        self, payment_id: str, booking_id: str, provider: str | None, amount: Any, failure_code: str
    ) -> None:
        """Operator-visible record of a refund the platform could not issue."""

        try:
            await self.session.execute(
                text("""
                    insert into payment_refunds
                      (payment_id, booking_id, provider, amount, status, reason,
                       idempotency_key, failure_code)
                    values (:p, :b, :provider, :amount, 'failed', :reason, :key, :code)
                    on conflict (payment_id, idempotency_key) do update
                      set status = 'failed', failure_code = excluded.failure_code
                      where payment_refunds.status = 'created'
                        and payment_refunds.refund_ref is null
                """),
                {"p": payment_id, "b": booking_id, "provider": provider, "amount": amount,
                 "reason": SALON_CLOSED_REASON, "key": CLOSURE_REFUND_KEY,
                 "code": failure_code[:120]},
            )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise

    async def list_unsettled_closure_refunds(self, user_id: str) -> list[str]:
        result = await self.session.execute(
            text(f"""
                select r.id from payment_refunds r
                join bookings b on b.id = r.booking_id
                where b.salon_id in ({_OWNED_SALONS})
                  and r.idempotency_key = :key and r.status = 'created'
                order by r.created_at, r.id
            """),
            {"uid": user_id, "key": CLOSURE_REFUND_KEY},
        )
        return [str(r[0]) for r in result.all()]

    # ---------------------------------------------------------------- erasure
    async def erase_database(
        self, user_id: str, role: str, staff_profile_ids: list[str] | None = None
    ) -> None:
        s = self.session
        try:
            await s.execute(text("select set_config('app.account_erasure', 'on', true)"))
            params = {"uid": user_id}
            await s.execute(text("select id from profiles where id=:uid for update"), params)
            if role == "owner":
                # Creation takes FOR SHARE on the same salon row before validating it.
                await s.execute(text("select id from salons where owner_id=:uid order by id for update"), params)
            await self._scrub_booking_audits(params)
            await self._scrub_post_baseline_footprint(params)
            await self._scrub_user_footprint(params)
            deletable_staff: list[str] = []
            if role == "owner":
                deletable_staff = await self._scrub_owner_business(params, staff_profile_ids or [])
            await s.execute(text("select erase_profile_references(:uid)"), params)
            await s.execute(text("delete from profiles where id = :uid"), params)
            for staff_id in deletable_staff:
                await s.execute(text("select erase_profile_references(:uid)"), {"uid": staff_id})
                await s.execute(text("delete from profiles where id = :uid"), {"uid": staff_id})
            await s.commit()
        except BaseException:
            await s.rollback()
            raise

    async def _scrub_booking_audits(self, params: dict[str, str]) -> None:
        """Fail closed during rollout if new audit tables lack their privacy migration."""
        state = (await self.session.execute(text("""
            select to_regclass('public.booking_customer_changes') is not null
                     or to_regclass('public.booking_finance_commands') is not null as has_audits,
                   to_regprocedure('public.erase_booking_audit_personal_data(uuid)') is not null as can_scrub
        """))).mappings().one()
        if state["has_audits"]:
            if not state["can_scrub"]:
                raise RuntimeError("booking_audit_privacy_migration_required")
            await self.session.execute(text("select public.erase_booking_audit_personal_data(:uid)"), params)

    async def _scrub_post_baseline_footprint(self, params: dict[str, str]) -> None:
        """Clear later support copies/diagnostics while retaining financial rows."""
        present = set((await self.session.execute(text("""
            select tablename from pg_catalog.pg_tables where schemaname='public'
              and tablename in ('payment_anomalies','payment_provider_account_audit','subscription_billing_records','support_tickets')
        """))).scalars().all())
        if not present:
            return
        if "support_tickets" in present or "subscription_billing_records" in present:
            ready = (await self.session.execute(text("""
                select to_regclass('public.support_erasure_events') is not null
                  and to_regprocedure('public.erase_subscription_benefit_text(uuid)') is not null
            """))).scalar_one()
            if not ready:
                raise RuntimeError("support_billing_privacy_migration_required")
        profile_row = (await self.session.execute(text("""
            select id,role::text as role,full_name,email,phone,avatar_url from profiles where id=:uid
        """), params)).mappings().one_or_none()
        if profile_row is None:
            return
        profile = dict(profile_row)
        diagnostics = {**params, "pattern": personal_text_pattern(profile), "redacted": "█"}
        if "support_tickets" in present:
            await self._scrub_support_footprint(params, profile)
        bookings = """select b.id from public.bookings b join public.salons s on s.id=b.salon_id
                      where b.customer_id=:uid or s.owner_id=:uid"""
        if "payment_anomalies" in present:
            await self.session.execute(text(f"""
                update payment_anomalies set detail=regexp_replace(detail,:pattern,:redacted,'gi')
                  where detail ~* :pattern and (
                  resolved_by=:uid or salon_id in ({_OWNED_SALONS}) or booking_id in ({bookings})
                  or payment_id in (select id from booking_payments where booking_id in ({bookings})))
            """), diagnostics)
        if "payment_provider_account_audit" in present:
            await self.session.execute(text(f"""
                update payment_provider_account_audit set detail=regexp_replace(detail,:pattern,:redacted,'gi')
                  where detail ~* :pattern
                  and (actor_id=:uid or salon_id in ({_OWNED_SALONS}))
            """), diagnostics)
        if "subscription_billing_records" in present:
            if profile["role"] == "owner":
                await self.session.execute(text("select public.erase_subscription_benefit_text(:uid)"), params)
            await self.session.execute(text(f"""
                update subscription_billing_records set failure_code=regexp_replace(failure_code,:pattern,:redacted,'gi')
                  where failure_code ~* :pattern
                  and (created_by=:uid or updated_by=:uid or salon_id in ({_OWNED_SALONS}))
            """), diagnostics)

    async def _scrub_support_footprint(self, params: dict[str, str], profile: dict) -> None:
        """Selectively anonymize known personal text and retain versioned case evidence."""
        # Reply use cases lock this same ticket before inserting messages/cached replies.
        tickets = (await self.session.execute(text("""
            select t.id from support_tickets t where t.customer_id=:uid
              or t.salon_id in (select id from salons where owner_id=:uid)
              or exists(select 1 from support_messages m where m.ticket_id=t.id and m.author_id=:uid)
            order by t.id for update of t
        """), params)).scalars().all()
        if not tickets:
            return
        values = {**params, "tickets": tickets, "pattern": personal_text_pattern(profile),
                  "owner": profile["role"] == "owner", "role": profile["role"], "removed": REMOVED_TEXT,
                  "redacted": "█"}
        await self.session.execute(text("""
            delete from payment_idempotency_keys where scope in (
              select 'support:reply:' || id::text from support_tickets where id=any(cast(:tickets as uuid[])))
              or (scope='support:create' and response_body->>'id' in (
                select id::text from support_tickets where id=any(cast(:tickets as uuid[]))))
        """), values)
        # Retained support history is restricted: cancel its local outbound and
        # delivery copies, including ambiguous quotes, without deleting case evidence.
        await self.session.execute(text("""
            delete from email_events where event_key in (
              select 'support_reply:'||id::text from support_messages where ticket_id=any(cast(:tickets as uuid[]))
              union all select 'support_confirmation:'||id::text from support_tickets where id=any(cast(:tickets as uuid[]))
              union all select 'support_admin:'||id::text from support_tickets where id=any(cast(:tickets as uuid[])))
        """), values)
        await self._redact_support_copies(values)
        # Capture authored text before overwriting it. Read bounded keyset pages
        # so a long support history never becomes one unbounded regex or payload.
        batch: list[str] = []
        size = 0
        after = None
        while True:
            originals = (await self.session.execute(text("""
                select id,body from support_messages where author_id=:uid
                  and ticket_id=any(cast(:tickets as uuid[])) and body<>:removed
                  and (cast(:after as uuid) is null or id>cast(:after as uuid))
                order by id limit 20
            """), {**values, "after": after})).mappings().all()
            if not originals:
                break
            for original in originals:
                body = original["body"]
                # Acknowledgements, punctuation and bare amounts are not reliable
                # evidence of a personal-data quote. Preserve ambiguous matches.
                if len(body.strip()) < 16 or not any(character.isalpha() for character in body):
                    continue
                literal = quoted_text_pattern(body)
                if batch and size + len(literal) > 16000:
                    await self._redact_support_copies({**values, "pattern": authored_quote_pattern(batch), "redacted": r"\1█"})
                    batch, size = [], 0
                batch.append(literal)
                size += len(literal) + 1
            after = originals[-1]["id"]
        if batch:
            await self._redact_support_copies({**values, "pattern": authored_quote_pattern(batch), "redacted": r"\1█"})
        await self.session.execute(text("""
            update support_messages set body=:removed where author_id=:uid
              and ticket_id=any(cast(:tickets as uuid[])) and body<>:removed
        """), values)
        await self.session.execute(text("""
            update support_tickets set retained_restricted=true,erasure_policy_version='support-erasure-v1',
                erasure_retention_reason='operational_review_pending'
              where id=any(cast(:tickets as uuid[])) and :owner
        """), values)
        await self.session.execute(text("""
            insert into support_erasure_events(ticket_id,actor_pseudonym,actor_role,policy_version,retention_reason)
              select id,public.booking_audit_identifier_hash('support-erasure',id::text||':'||cast(:uid as text)),
                :role,'support-erasure-v1','operational_review_pending'
              from support_tickets where id=any(cast(:tickets as uuid[])) and retained_restricted
              on conflict(ticket_id,actor_pseudonym,policy_version) do nothing
        """), values)
        await self.session.execute(text("""
            update support_tickets set customer_id=null
              where customer_id=:uid and retained_restricted and id=any(cast(:tickets as uuid[]))
        """), values)

    async def _redact_support_copies(self, values: dict) -> None:
        """Redact identified fragments while preserving surrounding case evidence."""
        await self.session.execute(text("""
            update support_messages set body=regexp_replace(body,:pattern,:redacted,'gi')
              where ticket_id=any(cast(:tickets as uuid[])) and author_id is distinct from :uid and body ~* :pattern
        """), values)
        await self.session.execute(text("""
            update support_tickets set subject=regexp_replace(subject,:pattern,:redacted,'gi')
              where id=any(cast(:tickets as uuid[])) and subject ~* :pattern
        """), values)

    async def _scrub_notifications(self, predicate: str, params: dict[str, Any]) -> None:
        """Anonymise other people's notifications that name a deleted person.

        Delivery/outbox error text can echo provider payloads, so it goes too. The
        predicate must not depend on the columns being rewritten.
        """

        s = self.session
        ids = f"select id from notifications where {predicate}"
        await s.execute(
            text(f"update notification_deliveries set error = null where notification_id in ({ids})"),
            params,
        )
        await s.execute(
            text(f"update notification_outbox set last_error = null where notification_id in ({ids})"),
            params,
        )
        await s.execute(
            text(f"""
                update notifications
                set title = :title, body = null, data = null
                where {predicate}
                  and (title is distinct from :title or body is not null or data is not null)
            """),
            {**params, "title": ANONYMISED_NOTIFICATION_TITLE},
        )

    async def _scrub_legacy_descriptions(self, params: dict[str, str]) -> None:
        """Erase owner metadata during rollout, without requiring removed columns."""
        s = self.session
        legacy = await s.execute(text("""
            select table_name from information_schema.columns
            where table_schema = 'public' and column_name = 'description'
              and table_name in ('salons', 'services')
        """))
        for table in legacy.scalars().all():
            if table == "salons":
                await s.execute(text("update salons set description = null where owner_id = :uid"), params)
            elif table == "services":
                await s.execute(text(f"update services set description = null where salon_id in ({_OWNED_SALONS})"), params)

    async def _scrub_user_footprint(self, params: dict[str, str]) -> None:
        """Everything that points at the person being erased, whatever their role."""

        s = self.session
        await s.execute(text("delete from notifications where user_id = :uid"), params)
        await s.execute(text("delete from device_tokens where user_id = :uid"), params)
        # Other people's inbox items that name this customer (owner/staff "X booked ...").
        await self._scrub_notifications(
            "user_id <> :uid and booking_id in (select id from bookings where customer_id = :uid)",
            params,
        )
        await s.execute(text("delete from salon_reports where reporter_id = :uid"), params)
        await s.execute(
            text("""
                update booking_action_requests
                set reason = case when requested_by = :uid then null else reason end,
                    decision_reason = case when decision = 'decline' then :removed end
                where requested_by = :uid
                   or booking_id in (select id from bookings where customer_id = :uid)
            """),
            {**params, "removed": REMOVED_TEXT},
        )
        await s.execute(
            text("""
                update bookings
                set customer_name = 'Deleted customer', customer_phone = null, notes = null,
                    cancellation_reason_code = null, cancellation_reason_text = null,
                    rejection_reason = case when status = 'rejected' then :removed end,
                    cancellation_reason = case when cancellation_reason = :closed
                                               then cancellation_reason end
                where customer_id = :uid
            """),
            {**params, "removed": REMOVED_TEXT, "closed": SALON_CLOSED_REASON},
        )
        # Financial rows are RETAINED (amounts, ids, provider references); only the
        # people on them are detached.
        await s.execute(text("update booking_payments set payer_id = null where payer_id = :uid"), params)
        await s.execute(
            text("update booking_payments set recorded_by = null where recorded_by = :uid"), params
        )
        await s.execute(text("delete from payment_idempotency_keys where actor_id = :uid"), params)

    async def _scrub_owner_business(self, params: dict[str, str], staff_ids: list[str]) -> list[str]:
        """Empty a closed salon down to an anonymous shell.

        Returns the staff profile ids that are safe to hard-delete (see below).
        """

        s = self.session
        owned = f"({_OWNED_SALONS})"
        # Re-run inside the erasure transaction: an order paid after the earlier step must not
        # leave a live renewal behind (idempotent; a late payment later hits 'blocked_closed').
        await SubscriptionBillingRepository(s).wind_down_salons(params["uid"])
        # Staff logins that existed only for these salons are separate people whose
        # profile (name, email, phone, avatar) would otherwise be banned but kept for
        # ever. Guard: staff role, no staff row at a salon this owner does not own, never a
        # customer, never an owner. Anything failing the guard stays banned, not deleted.
        deletable_staff: list[str] = []
        if staff_ids:
            rows = await s.execute(
                text(f"""
                    select p.id from profiles p
                    where p.id = any(cast(:ids as uuid[])) and p.role = 'staff' and p.id <> :uid
                      and not exists (select 1 from staff o where o.profile_id = p.id
                                      and o.salon_id not in {owned})
                      and not exists (select 1 from bookings b where b.customer_id = p.id)
                      and not exists (select 1 from salons x where x.owner_id = p.id)
                """),
                {**params, "ids": staff_ids},
            )
            deletable_staff = [str(r[0]) for r in rows.all()]
        if staff_ids:
            await s.execute(
                text("delete from payment_idempotency_keys where actor_id = any(cast(:ids as uuid[]))"),
                {"ids": staff_ids},
            )

        # Cascade FKs to salons never fire (salons are kept): delete explicitly.
        for table in SALON_CASCADE_TABLES + SALON_PROVIDER_REFERENCE_TABLES:
            await s.execute(text(f"delete from {table} where salon_id in {owned}"), params)
        await s.execute(
            text(
                "delete from blocked_slots where staff_id in "
                f"(select id from staff where salon_id in {owned})"
            ),
            params,
        )
        await s.execute(
            text(f"""
                update subscription_events set error_message = null
                where error_message is not null and salon_subscription_id in (
                  select id from salon_subscriptions where salon_id in {owned})
            """),
            params,
        )
        await s.execute(
            text(f"update salon_reports set details = '' where salon_id in {owned} and details <> ''"),
            params,
        )

        await s.execute(
            text("""
                update salons
                set is_active = false, name = :shell, city = null,
                    address = null, lat = null, lng = null, qr_image_url = null,
                    rejection_reason = null, working_hours = '{}'::jsonb,
                    qr_token = encode(gen_random_bytes(16), 'hex')
                where owner_id = :uid
            """),
            {**params, "shell": SHELL_SALON_NAME},
        )
        await s.execute(
            text(f"update services set photo_url = null where salon_id in {owned}"),
            params,
        )
        # During the coordinated rollout the old columns may still exist. Keep
        # erasure complete until reviewed 0041 drops them; never recreate them.
        await self._scrub_legacy_descriptions(params)
        await s.execute(
            text(f"""
                update staff_services set specialization = null
                where specialization is not null
                  and staff_id in (select id from staff where salon_id in {owned})
            """),
            params,
        )
        await s.execute(
            text(f"""
                update staff
                set name = 'Former staff', photo_url = null, specialization = null,
                    experience = null, profile_id = null, is_active = false
                where salon_id in {owned}
            """),
            params,
        )

        # Bookings stay (other customers' history) but lose owner-written free text, and
        # walk-in people - who have no account and no other holder - lose their details.
        await s.execute(
            text(f"""
                update bookings
                set rejection_reason = case when status = 'rejected' then :removed end,
                    cancellation_reason_code = null, cancellation_reason_text = null,
                    cancellation_reason = case when cancellation_reason = :closed
                                               then cancellation_reason end
                where salon_id in {owned}
                  and (cancellation_reason_code is not null or cancellation_reason_text is not null
                       or rejection_reason is distinct from case when status = 'rejected' then :removed end
                       or cancellation_reason is distinct from case when cancellation_reason = :closed
                                                                    then cancellation_reason end)
            """),
            {**params, "removed": REMOVED_TEXT, "closed": SALON_CLOSED_REASON},
        )
        await s.execute(
            text(f"""
                update bookings
                set customer_name = 'Deleted customer', customer_phone = null, notes = null
                where salon_id in {owned} and customer_id is null
                  and (customer_name <> 'Deleted customer' or customer_phone is not null
                       or notes is not null)
            """),
            params,
        )
        await s.execute(
            text(f"""
                update booking_action_requests
                set decision_reason = case when decision = 'decline' then :removed end
                where decision_reason is not null
                  and decision_reason is distinct from case when decision = 'decline' then :removed end
                  and booking_id in (select id from bookings where salon_id in {owned})
            """),
            {**params, "removed": REMOVED_TEXT},
        )
        # An owner-typed refund reason is free text; the closure code is not.
        await s.execute(
            text(f"""
                update payment_refunds set reason = null
                where reason is not null and reason <> :closed
                  and booking_id in (select id from bookings where salon_id in {owned})
            """),
            {**params, "closed": SALON_CLOSED_REASON},
        )
        # Whoever recorded a cash receipt (owner or staff) is detached; amounts stay.
        await s.execute(
            text(f"""
                update booking_payments set recorded_by = null
                where salon_id in {owned} and recorded_by is not null
            """),
            params,
        )
        # Customers' and staff inbox items about this salon may name the owner, the staff
        # or the salon; the cancellation notices written by the closure step are exempt.
        await self._scrub_notifications(
            f"""user_id <> :uid
                and booking_id in (select id from bookings where salon_id in {owned})
                and coalesce(data ->> 'reason', '') <> '{SALON_CLOSED_REASON}'""",
            params,
        )
        return deletable_staff

    async def profile_exists(self, user_id: str) -> bool:
        result = await self.session.execute(
            text("select exists (select 1 from profiles where id = :uid)"), {"uid": user_id}
        )
        return bool(result.scalar_one())
