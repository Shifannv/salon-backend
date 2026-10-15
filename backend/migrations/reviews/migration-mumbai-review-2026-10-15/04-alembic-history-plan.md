# Alembic history reconciliation — no execution

Sole head: `0037_customer_processing_charge`, 37 revisions. Destination
public.alembic_version has zero rows. No revision/head file changed. The three SQL
drafts have no assigned Alembic IDs. Provenance is schema restore plus Supabase supplements.
Never insert 37 historical rows, claim those revisions ran, replay base-to-head on
Mumbai or stamp 0037 despite known differences.

After separate design approval:

1. Resolve both legacy-column erasure classifications. Prepare three reviewed raw-SQL
   revisions sequentially after 0037: schema, security, signup. Review final IDs/links
   and non-destructive downgrade contract. Omit standalone BEGIN/COMMIT wrappers inside
   Alembic's transaction. No invented IDs or actual revisions in this bundle.
2. Build approved expected head in an explicitly authorized disposable PG17 environment
   with representative Supabase roles/defaults/Auth prerequisites. Document consolidated
   baseline/replay limitations; never silently hand-edit reference history/schema. No
   local or remote migration execution occurred this turn.
3. Test definitions, columns/collations, constraints/indexes, function body/owner/config,
   trigger event/state, RLS, column/object/effective/inherited/default ACLs and extensions.
   Verify no direct client booking mutation/RPC bypass, and test signup/erasure with
   synthetic disposable records. Preserve managed ACLs and existing backend access.
4. Compare approved expected head to fresh Mumbai metadata. All three drafts currently
   predict no destination change: columns, ACLs, config and signup already match their
   proposed targets. Prove that before deciding whether any SQL needs applying.
5. Stop on every unresolved mismatch. Once exact approved expected-head equality is
   proven, present an exact UNEXECUTED stamp command using the actual approved new ID
   and request separate approval. Do not stamp an old head solely to replay already
   present effects. Supabase migration history remains intact and separate.
6. Record schema-restore provenance: stamping a matching baseline is not execution of
   its historical revisions. Future ordinary upgrades follow only after reconciliation.

No executable stamp command or history INSERT/UPDATE/DELETE is supplied: no verified
matching new head exists. Future history reversal requires complete approved before/after
version metadata, separate approval, and no application-schema downgrade to reverse a
history-only stamp. Current execution and stamp authorization: none.
