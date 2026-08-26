"""Add is_active soft-delete column to salon_images.

Salon images are platform data and must be soft-deleted (is_active = false)
rather than hard-deleted.  The DELETE /owner/me/images/{id} endpoint was
previously a 501 stub waiting for this column.

After this migration:
- list_salon_images filters on is_active = true (active images only).
- DELETE soft-sets is_active = false and best-effort deletes the R2 object.

Revision ID: 0008_salon_images_soft_delete
Revises: 0007_salon_qr_image_url
Create Date: 2026-08-24
"""

from alembic import op

revision = "0008_salon_images_soft_delete"
down_revision = "0007_salon_qr_image_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_active column and supporting index to salon_images."""
    op.execute(
        """
        alter table salon_images
          add column if not exists is_active boolean not null default true;
        """
    )
    op.execute(
        """
        create index if not exists idx_salon_images_active
          on salon_images(salon_id, is_active, sort_order);
        """
    )


def downgrade() -> None:
    """Remove is_active column and its index from salon_images."""
    op.execute("drop index if exists idx_salon_images_active;")
    op.execute("alter table salon_images drop column if exists is_active;")
