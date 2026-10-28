"""Blocker counts and verification-challenge statements."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.infrastructure.db.repositories.account_deletion.constants import (
    _CHALLENGE_COLUMNS,
    _OWNED_SALONS,
)


class _ChallengeMixin:
    session: AsyncSession

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
