"""Super-admin discovery visibility and home placement controls."""

from alembic import op

revision = "0019_discovery_placement"
down_revision = "0018_subscription_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        alter table salons
          add column discovery_visibility text not null default 'listed'
            check (discovery_visibility in ('listed', 'search_only', 'hidden')),
          add column home_placement text not null default 'normal'
            check (home_placement in ('top', 'normal', 'below', 'random'));
    """)
    op.execute("""
        create function guard_salon_discovery_placement() returns trigger
        language plpgsql set search_path = public as $$
        begin
          if auth.uid() is null then
            if current_user in ('anon', 'authenticated') then
              raise exception 'Authenticated salon actor required' using errcode = '42501';
            end if;
            return new;
          end if;
          if is_super_admin() then return new; end if;
          if (tg_op = 'INSERT' and
               (new.discovery_visibility <> 'listed' or new.home_placement <> 'normal'))
             or (tg_op = 'UPDATE' and
               (new.discovery_visibility is distinct from old.discovery_visibility
                or new.home_placement is distinct from old.home_placement)) then
            raise exception 'Super admin required to change discovery placement'
              using errcode = '42501';
          end if;
          return new;
        end $$;
    """)
    op.execute("""
        create trigger salons_guard_discovery_placement before insert or update on salons
        for each row execute function guard_salon_discovery_placement();
    """)


def downgrade() -> None:
    op.execute("""
        drop trigger salons_guard_discovery_placement on salons;
    """)
    op.execute("drop function guard_salon_discovery_placement()")
    op.execute("alter table salons drop column home_placement, drop column discovery_visibility")
