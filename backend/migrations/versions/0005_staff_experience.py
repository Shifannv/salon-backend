"""Add staff experience.

Revision ID: 0005_staff_experience
Revises: 0004_service_duration_slot_steps
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_staff_experience"
down_revision = "0004_service_duration_slot_steps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store the owner-entered professional experience label for staff."""

    op.add_column("staff", sa.Column("experience", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove staff experience."""

    op.drop_column("staff", "experience")
