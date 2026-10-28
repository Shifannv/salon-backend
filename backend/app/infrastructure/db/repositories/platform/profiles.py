"""Profile reads and writes."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
)


class ProfilesMixin:
    """Profile reads and writes."""

    session: AsyncSession

    async def update_profile(self, profile_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Update the actor's profile.

        ``values`` contains only keys the caller explicitly set (``exclude_unset`` in the
        Pydantic schema).  An explicit ``null`` clears the corresponding nullable column
        (phone, full_name, avatar_url).  Omitted keys are not in the dict at all, so they
        are never touched.
        """

        # Empty dict → nothing was sent; return the current row unchanged.
        if not values:
            profile = await self.get_profile(profile_id)
            if profile is None:
                raise NotFoundError("Profile not found")
            return profile

        assignments = ", ".join(self._sql_assignment(key) for key in values)
        result = await self.session.execute(
            text(
                f"""
                update profiles
                set {assignments}
                where id = :profile_id
                returning id, role, full_name, email, phone, phone_verified, avatar_url, is_active
                """
            ),
            {**values, "profile_id": profile_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise NotFoundError("Profile not found")
        await self.session.commit()
        return self._profile_response(row)

    async def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        """Read a profile row."""

        result = await self.session.execute(
            text(
                """
                select id, role, full_name, email, phone, phone_verified, avatar_url, is_active
                from profiles
                where id = :profile_id
                """
            ),
            {"profile_id": profile_id},
        )
        row = result.mappings().one_or_none()
        return self._profile_response(row) if row else None
