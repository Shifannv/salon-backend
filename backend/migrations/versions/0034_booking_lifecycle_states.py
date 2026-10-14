"""Prepare booking lifecycle enum values before transactional guards use them.

Revision ID: 0034_booking_lifecycle_states
Revises: 0033_payment_fee_snapshot
"""

from alembic import op

revision = "0034_booking_lifecycle_states"
down_revision = "0033_payment_fee_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires enum additions to commit before they can be used.
    with op.get_context().autocommit_block():
        op.execute("alter type public.booking_status add value if not exists 'checked_in'")
        op.execute("alter type public.booking_status add value if not exists 'no_show'")


def downgrade() -> None:
    # Enum labels cannot be removed without replacing the type. Retain unused labels.
    pass
