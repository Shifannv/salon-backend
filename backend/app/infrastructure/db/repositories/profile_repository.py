"""SQL profile repository adapter."""

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.profile import Profile, Role
from app.domain.repositories.profile_repository import ProfileRepository


class SQLProfileRepository(ProfileRepository):
    """Read profiles from Postgres."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, profile_id: str) -> Profile | None:
        """Return a profile by id."""

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
        return _profile_from_row(row) if row else None

    async def grant_owner_role(self, profile_id: str) -> Profile | None:
        """Promote an active customer profile to owner.

        The ``role = 'customer'`` predicate is what makes this safe to call on every
        sign-in: an owner, a staff member, or the super admin matches no row and is
        returned unchanged by the caller rather than being rewritten.
        """

        result = await self.session.execute(
            text(
                """
                update profiles
                set role = 'owner'
                where id = :profile_id
                  and is_active
                  and role = 'customer'
                returning id, role, full_name, email, phone, phone_verified, avatar_url, is_active
                """
            ),
            {"profile_id": profile_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        await self.session.commit()
        return _profile_from_row(row)


def _profile_from_row(row: RowMapping) -> Profile:
    return Profile(
        id=str(row["id"]),
        role=Role(str(row["role"])),
        full_name=row["full_name"],
        email=row["email"],
        phone=row["phone"],
        phone_verified=bool(row["phone_verified"]),
        avatar_url=row["avatar_url"],
        is_active=bool(row["is_active"]),
    )
