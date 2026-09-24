"""Store owner-entered booking delay estimates.

Revision ID: 0012_booking_delay
Revises: 0011_holiday_soft_delete
"""

from alembic import op

revision = "0012_booking_delay"
down_revision = "0011_holiday_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table bookings add column if not exists "
        "estimated_end_datetime timestamptz"
    )


def downgrade() -> None:
    op.execute("alter table bookings drop column if exists estimated_end_datetime")
