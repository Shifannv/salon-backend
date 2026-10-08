"""Repair the booking cancellation reason column on drifted databases.

Revision ID: 0014_repair_cancel_reason
Revises: 0013_booking_action_requests
"""

from alembic import op

revision = "0014_repair_cancel_reason"
down_revision = "0013_booking_action_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 0009 introduced this column. Some databases report 0013 while
    # lacking it, so repeat the additive operation without touching existing data.
    op.execute("alter table bookings add column if not exists cancellation_reason text")


def downgrade() -> None:
    # Revision 0009 still owns this column. Keep it when rolling back this repair.
    pass
