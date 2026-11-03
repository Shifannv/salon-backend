"""Consent records: newest row per kind is the current answer."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ConsentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def latest(self, user_id: str) -> dict[str, dict[str, Any]]:
        """The current answer per kind: ``{"terms": {"version": ..., "granted": ...}, ...}``."""

        result = await self.session.execute(
            text(
                """select distinct on (kind) kind, version, granted
                   from user_consents where user_id = cast(:user_id as uuid)
                   order by kind, seq desc"""
            ),
            {"user_id": user_id},
        )
        return {row["kind"]: {"version": row["version"], "granted": row["granted"]} for row in result.mappings()}

    async def record(self, user_id: str, source: str, answers: list[tuple[str, str, bool]]) -> None:
        """Append one row per ``(kind, version, granted)`` and commit."""

        for kind, version, granted in answers:
            await self.session.execute(
                text(
                    """insert into user_consents (user_id, kind, version, granted, source)
                       values (cast(:user_id as uuid), :kind, :version, :granted, :source)"""
                ),
                {"user_id": user_id, "kind": kind, "version": version, "granted": granted, "source": source},
            )
        await self.session.commit()
