"""Capture Google OAuth metadata in new profiles.

Revision ID: 0003_google_oauth_metadata
Revises: 0002_notifications_read_at
Create Date: 2026-08-10
"""

from alembic import op

revision = "0003_google_oauth_metadata"
down_revision = "0002_notifications_read_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update auth-user profile creation for OAuth metadata."""

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
            coalesce(
              new.raw_user_meta_data ->> 'full_name',
              new.raw_user_meta_data ->> 'name',
              ''
            ),
            coalesce(
              new.raw_user_meta_data ->> 'avatar_url',
              new.raw_user_meta_data ->> 'picture'
            ),
            coalesce((new.raw_user_meta_data ->> 'role')::user_role, 'customer')
          )
          on conflict (id) do nothing;
          return new;
        end $$;
        """
    )


def downgrade() -> None:
    """Restore the baseline profile creation function."""

    op.execute(
        """
        create or replace function handle_new_user()
        returns trigger language plpgsql security definer set search_path = public as $$
        begin
          insert into public.profiles (id, email, phone, full_name, role)
          values (
            new.id,
            new.email,
            new.phone,
            coalesce(new.raw_user_meta_data ->> 'full_name', ''),
            coalesce((new.raw_user_meta_data ->> 'role')::user_role, 'customer')
          )
          on conflict (id) do nothing;
          return new;
        end $$;
        """
    )
