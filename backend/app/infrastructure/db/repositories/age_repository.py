"""Date of birth and guardian approval records."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def birth_date(self, user_id: str) -> date | None:
        result = await self.session.execute(
            text("select date_of_birth from profiles where id = cast(:u as uuid)"), {"u": user_id}
        )
        return result.scalar_one_or_none()

    async def set_birth_date(self, user_id: str, birth_date: date) -> date:
        """Store the date once. Returns the date now on file (an earlier one wins)."""

        result = await self.session.execute(
            text(
                """update profiles set date_of_birth = coalesce(date_of_birth, :d)
                   where id = cast(:u as uuid) returning date_of_birth"""
            ),
            {"u": user_id, "d": birth_date},
        )
        stored = result.scalar_one()
        await self.session.commit()
        return stored

    async def open_guardian_request(self, user_id: str) -> dict[str, Any] | None:
        """The pending or approved row, locked for this transaction."""

        result = await self.session.execute(
            text(
                """select id::text as id, status, guardian_phone_hash, guardian_phone_last4, code_hash,
                          code_expires_at, attempts, sends, last_sent_at, created_at
                   from guardian_consents
                   where user_id = cast(:u as uuid) and status in ('pending', 'approved')
                   for update"""
            ),
            {"u": user_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def recent_sends(self, user_id: str, since: datetime) -> tuple[int, datetime | None]:
        """Codes sent to any guardian number since ``since`` and the time of the latest one.

        Counted across every request, so withdrawing and starting again cannot reset the limit.
        """

        result = await self.session.execute(
            text(
                """select coalesce(sum(sends), 0)::int as sends, max(last_sent_at) as last_sent_at
                   from guardian_consents
                   where user_id = cast(:u as uuid) and last_sent_at >= :since"""
            ),
            {"u": user_id, "since": since},
        )
        row = result.mappings().one()
        return row["sends"], row["last_sent_at"]

    async def lock_profile(self, user_id: str) -> None:
        await self.session.execute(
            text("select id from profiles where id = cast(:u as uuid) for no key update"), {"u": user_id}
        )

    async def start_request(
        self, user_id: str, phone_hash: str, last4: str, code_hash: str, expires_at: datetime
    ) -> None:
        await self.session.execute(
            text(
                """insert into guardian_consents
                     (user_id, guardian_phone_hash, guardian_phone_last4, code_hash, code_expires_at, sends, last_sent_at)
                   values (cast(:u as uuid), :ph, :l4, :ch, :exp, 1, now())"""
            ),
            {"u": user_id, "ph": phone_hash, "l4": last4, "ch": code_hash, "exp": expires_at},
        )

    async def resend(
        self, request_id: str, phone_hash: str, last4: str, code_hash: str, expires_at: datetime
    ) -> None:
        await self.session.execute(
            text(
                """update guardian_consents
                   set guardian_phone_hash = :ph, guardian_phone_last4 = :l4, code_hash = :ch,
                       code_expires_at = :exp, attempts = 0, sends = sends + 1, last_sent_at = now()
                   where id = cast(:id as uuid) and status = 'pending'"""
            ),
            {"id": request_id, "ph": phone_hash, "l4": last4, "ch": code_hash, "exp": expires_at},
        )

    async def count_attempt(self, request_id: str) -> None:
        await self.session.execute(
            text("update guardian_consents set attempts = attempts + 1 where id = cast(:id as uuid)"),
            {"id": request_id},
        )

    async def clear_code(self, request_id: str) -> None:
        await self.session.execute(
            text("update guardian_consents set code_hash = null where id = cast(:id as uuid)"), {"id": request_id}
        )

    async def approve(self, request_id: str) -> None:
        await self.session.execute(
            text(
                """update guardian_consents
                   set status = 'approved', approved_at = now(), code_hash = null, code_expires_at = null
                   where id = cast(:id as uuid) and status = 'pending'"""
            ),
            {"id": request_id},
        )

    async def revoke(self, request_id: str) -> None:
        await self.session.execute(
            text(
                """update guardian_consents set status = 'revoked', revoked_at = now(), code_hash = null
                   where id = cast(:id as uuid) and status in ('pending', 'approved')"""
            ),
            {"id": request_id},
        )

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
