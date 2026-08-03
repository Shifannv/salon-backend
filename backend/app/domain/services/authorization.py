"""Pure authorization rules mirroring database RLS policy intent."""

from app.domain.entities.profile import Profile, Role


def is_super_admin(actor: Profile) -> bool:
    """Return whether the actor is a super administrator."""

    return actor.role == Role.super_admin


def can_read_own_profile(actor: Profile, profile_id: str) -> bool:
    """Return whether the actor may read the target profile."""

    return is_super_admin(actor) or actor.id == profile_id


def require_active(actor: Profile) -> None:
    """Reject inactive actors before use cases proceed."""

    from app.core.exceptions import ForbiddenError

    if not actor.is_active:
        raise ForbiddenError("This account is inactive")
