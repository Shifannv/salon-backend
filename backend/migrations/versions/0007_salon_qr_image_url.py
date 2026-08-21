"""Add qr_image_url to salons table.

Stores the permanent Cloudflare R2 public URL of the salon's walk-in QR code PNG.

Generated once on the first GET /salons/me/qr call after this migration is applied.
The column is nullable — NULL means the QR image has not yet been uploaded to R2;
the endpoint falls back to generating the image on the fly until it is.

Revision ID: 0007_salon_qr_image_url
Revises: 0006_enable_realtime
Create Date: 2026-08-21
"""

from alembic import op

revision = "0007_salon_qr_image_url"
down_revision = "0006_enable_realtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add qr_image_url column to salons."""
    op.execute(
        """
        alter table salons
          add column if not exists qr_image_url text;
        """
    )


def downgrade() -> None:
    """Drop qr_image_url column from salons."""
    op.execute("alter table salons drop column if exists qr_image_url;")
