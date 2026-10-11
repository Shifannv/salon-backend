"""Trust only operator-controlled metadata when assigning a new profile role.

Revision ID: 0024_secure_new_user_role
Revises: 0023_notification_data
Create Date: 2026-10-11 11:44:15.138823
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024_secure_new_user_role"
down_revision: str | Sequence[str] | None = "0023_notification_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Use app metadata for trusted provisioning; ordinary signups remain customers."""
    op.execute(
        """
        create or replace function handle_new_user()
        returns trigger language plpgsql security definer set search_path = public as $$
        begin
          insert into public.profiles (id, email, phone, full_name, avatar_url, role)
          values (
            new.id,
            new.email,
            new.phone,
            coalesce(new.raw_user_meta_data ->> 'full_name',
                     new.raw_user_meta_data ->> 'name', ''),
            coalesce(new.raw_user_meta_data ->> 'avatar_url',
                     new.raw_user_meta_data ->> 'picture'),
            case
              when new.raw_app_meta_data ->> 'role' in
                   ('super_admin', 'owner', 'staff', 'customer')
                then (new.raw_app_meta_data ->> 'role')::user_role
              else 'customer'::user_role
            end
          )
          on conflict (id) do nothing;
          return new;
        end $$;
        """
    )
    op.execute("revoke execute on function public.handle_new_user() from public, anon, authenticated")


def downgrade() -> None:
    """Restore the previous metadata behavior for a strict schema rollback."""
    op.execute(
        """
        create or replace function handle_new_user()
        returns trigger language plpgsql security definer set search_path = public as $$
        begin
          insert into public.profiles (id, email, phone, full_name, avatar_url, role)
          values (
            new.id,
            new.email,
            new.phone,
            coalesce(new.raw_user_meta_data ->> 'full_name',
                     new.raw_user_meta_data ->> 'name', ''),
            coalesce(new.raw_user_meta_data ->> 'avatar_url',
                     new.raw_user_meta_data ->> 'picture'),
            coalesce((new.raw_user_meta_data ->> 'role')::user_role, 'customer')
          )
          on conflict (id) do nothing;
          return new;
        end $$;
        """
    )
    op.execute("revoke execute on function public.handle_new_user() from public, anon, authenticated")
