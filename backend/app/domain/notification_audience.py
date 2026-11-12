"""Maps notification types to their intended audience (owner or customer).

Each notification row targets exactly one person. The audience tells the push
gateway which app's device tokens to use for delivery, and lets the list
endpoint filter by app without client-side type logic.

Call sites that send ``booking_cancelled`` must pass ``audience`` explicitly:
the type is used for both customers (salon cancelled their booking) and owners
(customer cancelled their own booking).
"""

_AUDIENCE_BY_TYPE: dict[str, str] = {
    # Owner-side
    "new_booking": "owner",
    "payment_confirmation_requested": "owner",
    "cancellation_requested": "owner",
    "approval_status": "owner",
    "payout_update": "owner",
    "payout_updated": "owner",
    "booking_customer_on_the_way": "owner",
    "booking_customer_not_coming": "owner",
    "booking_no_show_auto": "owner",
    # Customer-side
    "booking_requested": "customer",
    "booking_confirmed": "customer",
    "booking_rejected": "customer",
    "booking_completed": "customer",
    "booking_no_show": "customer",
    "booking_no_show_warning": "customer",
    "booking_no_show_warning_withdrawn": "customer",
    "booking_cancelled_closure": "customer",
    "payment_received": "customer",
    "payment_not_received": "customer",
    "cancellation_approved": "customer",
    "cancellation_declined": "customer",
    "booking_delayed": "customer",
    # booking_cancelled: intentionally absent — audience depends on context.
    # booking_changed: sent by SQL triggers to both parties — leave NULL.
    # system: ad-hoc admin messages — leave NULL (sent to all).
}


def audience_for(notification_type: str) -> str | None:
    """Return 'owner', 'customer', or None when the type is unknown or shared."""
    return _AUDIENCE_BY_TYPE.get(notification_type)
