"""Shared constants for the account-deletion repository mixins."""

_CHALLENGE_COLUMNS = (
    "id, user_id, channel, contact_hash, status, attempts, max_attempts, resend_count, "
    "last_sent_at, expires_at, confirmation_hash, "
    "extract(epoch from (now() - last_sent_at)) as seconds_since_sent"
)
_OWNED_SALONS = "select id from salons where owner_id = :uid"

# Salons are soft-deactivated, never deleted, so ``on delete cascade`` foreign keys to
# salons(id) NEVER fire. Every such table must be emptied explicitly by
# ``_scrub_owner_business``. tests/unit/test_account_erasure_schema_guard.py fails when a
# migration adds a cascade FK to salons that is missing from this tuple.
SALON_CASCADE_TABLES: tuple[str, ...] = (
    "salon_images",
    "salon_holidays",
    "blocked_slots",
    "salon_payout_accounts",
    "salon_payout_account_history",
    "salon_access",
)
# Plain (NO ACTION) salon references that hold provider-side identifiers: also emptied.
SALON_PROVIDER_REFERENCE_TABLES: tuple[str, ...] = (
    "subscription_provider_accounts",
    "payment_provider_accounts",
)

SALON_CLOSED_REASON = "salon_closed"
CLOSURE_REFUND_KEY = "salon_closed"
SHELL_SALON_NAME = "Closed salon"
REMOVED_TEXT = "Removed"
ANONYMISED_NOTIFICATION_TITLE = "Booking update"

CLOSURE_NOTICE_BASE = "This salon has closed, so your booking has been cancelled."
CLOSURE_NOTICE_ONLINE = " Any online payment you made will be refunded to your original payment method."
CLOSURE_NOTICE_MANUAL = (
    " A payment you made directly to the salon is not refunded by the platform."
)

