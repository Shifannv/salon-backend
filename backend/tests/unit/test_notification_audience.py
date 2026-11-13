"""Type-to-audience mapping used to route notifications to the right app."""

from app.domain.notification_audience import audience_for


def test_owner_types_resolve_to_owner() -> None:
    for notification_type in (
        "new_booking",
        "payment_confirmation_requested",
        "cancellation_requested",
        "approval_status",
        "payout_update",
        "payout_updated",
    ):
        assert audience_for(notification_type) == "owner"


def test_customer_types_resolve_to_customer() -> None:
    for notification_type in (
        "booking_requested",
        "booking_confirmed",
        "booking_rejected",
        "booking_completed",
        "booking_no_show",
        "booking_cancelled_closure",
        "payment_received",
        "payment_not_received",
        "cancellation_approved",
        "cancellation_declined",
        "booking_delayed",
    ):
        assert audience_for(notification_type) == "customer"


def test_ambiguous_and_unknown_types_resolve_to_none() -> None:
    # booking_cancelled is sent to either party depending on context, so callers
    # must pass audience explicitly; it must never be auto-resolved.
    for notification_type in ("booking_cancelled", "booking_changed", "system", "unknown_type"):
        assert audience_for(notification_type) is None
