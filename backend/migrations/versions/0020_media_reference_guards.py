"""Serialize all media references with cleanup and block client URL bypasses.

RLS permits some Supabase Data API writes. API-only locks cannot protect cleanup
against those writes, so the guard is required before enabling retirement.
"""

from alembic import op

revision = "0020_media_reference_guards"
down_revision = "0019_discovery_placement"
branch_labels = None
depends_on = None

MEDIA_COLUMNS = (
    ("profiles", "avatar_url"), ("staff", "photo_url"), ("salon_images", "url"),
    ("services", "photo_url"), ("service_categories", "image_url"),
    ("service_subcategories", "image_url"), ("salons", "qr_image_url"),
)


def upgrade() -> None:
    op.execute("""
        create function guard_media_reference() returns trigger
        language plpgsql security invoker set search_path = pg_catalog as $$
        declare
          media_url text;
          previous_url text;
        begin
          media_url := to_jsonb(new) ->> tg_argv[0];
          if tg_op = 'UPDATE' then
            previous_url := to_jsonb(old) ->> tg_argv[0];
          end if;
          if media_url is null then return new; end if;
          if tg_table_name = 'profiles' and (
             media_url in ('avatar:curly', 'avatar:beard', 'avatar:geek') or
             media_url ~ '^__char__char-([1-9]|1[0-5])$'
          ) then return new; end if;
          perform pg_advisory_xact_lock(hashtextextended(media_url, 0));
          if media_url is distinct from previous_url and
             current_user in ('anon', 'authenticated') then
            raise exception 'Use the backend image upload API to assign media'
              using errcode = '42501';
          end if;
          return new;
        end;
        $$;
    """)
    for table, column in MEDIA_COLUMNS:
        op.execute(f"""
            create trigger media_reference_guard before insert or update on {table}
            for each row execute function guard_media_reference('{column}');
        """)


def downgrade() -> None:
    for table, _ in MEDIA_COLUMNS:
        op.execute(f"drop trigger if exists media_reference_guard on {table};")
    op.execute("drop function if exists guard_media_reference();")
