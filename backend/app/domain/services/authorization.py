"""Pure authorization rules mirroring database RLS policy intent."""

from app.domain.entities.profile import Profile, Role


def is_super_admin(actor: Profile) -> bool:
    """True for the super_admin role only."""
    return actor.role == Role.super_admin


def is_owner(actor: Profile) -> bool:
    """True for salon owners only."""
    return actor.role == Role.owner


def is_staff(actor: Profile) -> bool:
    """True for staff members only."""
    return actor.role == Role.staff


def is_owner_or_staff(actor: Profile) -> bool:
    """True for salon owners and staff — can access the salon workspace."""
    return actor.role in {Role.owner, Role.staff, Role.super_admin}


def is_customer(actor: Profile) -> bool:
    """True for the customer role only."""
    return actor.role == Role.customer


def can_read_own_profile(actor: Profile, profile_id: str) -> bool:
    """Return whether the actor may read the target profile."""

    return is_super_admin(actor) or actor.id == profile_id


def require_active(actor: Profile) -> None:
    """Reject inactive actors before use cases proceed."""

    from app.core.exceptions import ForbiddenError

    if not actor.is_active:
        raise ForbiddenError("This account is inactive")
