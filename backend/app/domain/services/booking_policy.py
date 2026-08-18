"""Booking policy domain service.

Pure Python rules for which actors may perform which booking lifecycle
transitions. Authorization belongs in the use-case (application) layer, but
the *rules* themselves are pure domain knowledge and live here.

RLS equivalents:
  - bookings_owner_update  →  can_approve, can_reject, can_complete, can_record_payment
  - bookings_customer_cancel →  can_cancel (customer branch)
"""

from app.domain.entities.booking import BookingSource, BookingStatus
from app.domain.entities.profile import Profile, Role


def can_approve(actor: Profile) -> bool:
    """Owners and staff may approve pending bookings."""
    return actor.role in {Role.owner, Role.staff}


def can_reject(actor: Profile) -> bool:
    """Owners and staff may reject pending bookings."""
    return actor.role in {Role.owner, Role.staff}


def can_complete(actor: Profile) -> bool:
    """Owners and staff may mark a booking as completed."""
    return actor.role in {Role.owner, Role.staff}


def can_cancel(actor: Profile) -> bool:
    """Any authenticated actor may cancel a booking they own."""
    return actor.role in {Role.owner, Role.staff, Role.customer}


def can_record_payment(actor: Profile) -> bool:
    """Only owners and staff may record payment."""
    return actor.role in {Role.owner, Role.staff}


def can_create_manual_walkin(actor: Profile) -> bool:
    """Manual walk-in bookings require salon workspace access."""
    return actor.role in {Role.owner, Role.staff}


def valid_source_for_actor(actor: Profile, source: str) -> bool:
    """Return True if the booking source is consistent with the actor's role."""
    if source == BookingSource.app:
        return actor.role == Role.customer
    if source == BookingSource.manual_walkin:
        return actor.role in {Role.owner, Role.staff}
    if source == BookingSource.qr_walkin:
        # qr_walkin is customer-created; could be an anonymous auth user
        return actor.role == Role.customer
    return False


def allowed_status_transitions(current: str) -> set[str]:
    """Return the set of status values this booking may move to.

    Guards which transitions are physically possible regardless of actor.
    """
    transitions: dict[str, set[str]] = {
        BookingStatus.pending: {
            BookingStatus.confirmed,
            BookingStatus.rejected,
            BookingStatus.cancelled,
        },
        BookingStatus.confirmed: {BookingStatus.completed, BookingStatus.cancelled},
        BookingStatus.rejected: set(),
        BookingStatus.completed: set(),
        BookingStatus.cancelled: set(),
    }
    return transitions.get(current, set())
