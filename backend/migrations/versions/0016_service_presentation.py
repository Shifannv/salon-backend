"""Add salon-specific service names and photos without changing the catalog."""

from alembic import op

revision = "0016_service_presentation"
down_revision = "0015_salon_admin_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table services add column category_name varchar(80)")
    op.execute("alter table services add column subcategory_name varchar(80)")
    op.execute("alter table services add column photo_url text")


def downgrade() -> None:
    op.execute("alter table services drop column photo_url")
    op.execute("alter table services drop column subcategory_name")
    op.execute("alter table services drop column category_name")
