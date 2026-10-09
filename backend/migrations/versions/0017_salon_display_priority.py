"""Add super-admin controlled salon display priority for public discovery.

Higher values rank first. Existing salons receive 0. Only super admins may change it.
Revision ID: 0017_salon_display_priority
Revises: 0016_service_presentation
"""

from alembic import op

revision = "0017_salon_display_priority"
down_revision = "0016_service_presentation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
alter table salons
  add column display_priority integer not null default 0
  constraint salons_display_priority_range check (display_priority between 0 and 100000);
        """
    )
    op.execute(
        """
-- RLS lets owners edit their salon row, so protect the ranking column independently.
create function guard_salon_display_priority() returns trigger
language plpgsql set search_path = public as $$
begin
  if auth.uid() is null then
    -- Trusted migration/maintenance sessions have no authenticated actor.
    -- Data API roles must never bypass the guard by omitting their subject.
    if current_user in ('anon', 'authenticated') then
      raise exception 'Authenticated salon actor required' using errcode = '42501';
    end if;
    return new;
  end if;
  if is_super_admin() then return new; end if;
  if (tg_op = 'INSERT' and new.display_priority <> 0)
     or (tg_op = 'UPDATE' and new.display_priority is distinct from old.display_priority) then
    raise exception 'Super admin required to change display priority' using errcode = '42501';
  end if;
  return new;
end $$;
        """
    )
    op.execute(
        """
create trigger salons_guard_display_priority before insert or update on salons
for each row execute function guard_salon_display_priority();
        """
    )


def downgrade() -> None:
    op.execute("drop trigger salons_guard_display_priority on salons")
    op.execute("drop function guard_salon_display_priority()")
    op.execute("alter table salons drop column display_priority")
