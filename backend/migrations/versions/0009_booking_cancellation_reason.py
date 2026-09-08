"""Add cancellation_reason column to bookings.

When a barber/owner cancels a booking they must provide a reason.
This column stores that reason so it can be displayed to the customer
alongside the cancellation notification.

The existing rejection_reason column already handles rejections.
This column is the parallel for cancellations initiated by the salon side.

Revision ID: 0009_booking_cancellation_reason
Revises: 0008_salon_images_soft_delete
Create Date: 2026-09-07
"""

from alembic import op

revision = "0009_booking_cancellation_reason"
down_revision = "0008_salon_images_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add cancellation_reason column to bookings table."""
    op.execute(
        """
        alter table bookings
          add column if not exists cancellation_reason text;
        """
    )


def downgrade() -> None:
    """Remove cancellation_reason column from bookings table."""
    op.execute("alter table bookings drop column if exists cancellation_reason;")
