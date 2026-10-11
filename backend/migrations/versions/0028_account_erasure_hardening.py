"""Account erasure hardening.

* ``erase_profile_references`` also clears RESTRICT foreign keys to profiles. It used to
  handle only NO ACTION (``confdeltype = 'a'``), so a future ``on delete restrict`` audit
  column would have made profile deletion fail forever.
* A partial index serving the operator's stale-request query
  (``status <> 'completed' and requested_at < now() - interval '1 hour'``).
* ``account_deletion_requests`` gains no columns: the cancel/refund/settle phases are
  recorded as boolean keys inside the existing ``step_state`` jsonb.

Everything else this hardening needs is application SQL in
``account_deletion_repository.py`` (explicit deletes for tables whose ``on delete cascade``
to ``salons`` never fires because salons are only deactivated).

Reviewed deploy step only; never run from API startup. Requires 0027.

Revision ID: 0028_account_erasure_hardening
Revises: 0027_payout_account_audit
Create Date: 2026-10-12 00:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028_account_erasure_hardening"
down_revision: str | Sequence[str] | None = "0027_payout_account_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FUNCTION = """
    create or replace function erase_profile_references(p_user uuid) returns integer
    language plpgsql security invoker set search_path = public, pg_catalog as $$
    declare
      fk record;
      touched integer := 0;
      n integer;
    begin
      perform set_config('app.account_erasure', 'on', true);
      for fk in
        select c.conrelid::regclass as tbl, a.attname as col
        from pg_constraint c
        join pg_attribute a
          on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
        where c.contype = 'f'
          and c.confrelid = 'public.profiles'::regclass
          and c.confdeltype in (%s)
          and array_length(c.conkey, 1) = 1
      loop
        execute format('update %%s set %%I = null where %%I = $1', fk.tbl, fk.col, fk.col)
          using p_user;
        get diagnostics n = row_count;
        touched := touched + n;
      end loop;
      return touched;
    end $$;
"""


def upgrade() -> None:
    # asyncpg prepares each call: keep top-level SQL statements separate.
    op.execute(_FUNCTION % "'a', 'r'")
    op.execute("""
        revoke execute on function erase_profile_references(uuid)
          from public, anon, authenticated;
    """)
    op.execute("""
        create index if not exists idx_account_deletion_requests_open_age
          on account_deletion_requests (requested_at)
          where status <> 'completed';
    """)


def downgrade() -> None:
    op.execute("drop index if exists idx_account_deletion_requests_open_age;")
    op.execute(_FUNCTION % "'a'")
    op.execute("""
        revoke execute on function erase_profile_references(uuid)
          from public, anon, authenticated;
    """)
