---
name: knex-migration-drift
description: Diagnose "works locally but not on dev/staging" bugs caused by in-place edits to already-applied Knex migrations
type: debugging_technique
extracted_from: bestdoc super-request sequential sub-request bug (2026-04-30)
---

# Knex Migration Drift

## When this pattern applies

A feature works on one environment (usually local, freshly migrated) but fails on a long-lived environment (dev/staging/prod). The code references DB columns or tables, and the project uses Knex migrations.

Strong signals:
- "It works on my machine but not on dev"
- Errors like `column "X" does not exist` (or silent failures in code that swallows DB errors)
- Recently shipped feature touches a `knex_migrations`-tracked schema

## Root cause to suspect

Knex tracks migrations by **filename** in the `knex_migrations` table. Once a migration runs on an environment, Knex will never re-run it — even if the file's contents change. Devs sometimes "fix" a migration by editing the original file instead of adding a new one. Result:
- Local DB (fresh) runs the current version of the file → has new columns.
- Long-lived DB ran the old version → columns are missing, but Knex thinks the migration is done.

## Diagnostic steps

1. **Find the migration file in question.** Use `git log --oneline -- db/migrations/<file>` and look for *multiple* commits touching the same file. That's the smell.

2. **Inspect rewrite history.** `git log --all -p -- db/migrations/<file>` will show what the file originally looked like vs now. Note added columns/tables.

3. **Check the long-lived DB schema.** Connect to the failing environment and run `\d <table>` (Postgres) or `DESCRIBE <table>` (MySQL). Cross-reference with the current migration content.

4. **Check Knex's migration table.**
   ```sql
   SELECT name, batch, migration_time
   FROM knex_migrations
   WHERE name = '<migration_filename>';
   ```
   If listed but columns are missing, drift is confirmed.

5. **Trace error propagation.** Often the SQL error is swallowed by an outer try/catch (e.g., `addRequest` returning `undefined`), causing downstream null/empty fields rather than a visible crash. Don't expect a clean stack trace at the surface.

## Fix

- **Never** edit a migration after it's been deployed.
- Add a new follow-up migration with idempotent ops:
  ```js
  exports.up = async (knex) => {
    const has = await knex.schema.hasColumn('service', 'is_allowed_on_previous_delay');
    if (!has) {
      await knex.schema.alterTable('service', (t) => {
        t.boolean('is_allowed_on_previous_delay').defaultTo(false);
      });
    }
  };
  ```
- If a column was renamed in the in-place edit, add a follow-up that handles both: drop the old column if exists, add the new one if not.

## Related anti-patterns to flag in review

- Any PR that modifies an existing migration file (vs adding a new one) deserves a comment.
- Models or query modifiers (e.g., Objection's `basicSelects`) referencing columns whose migration history shows in-place edits.
- Multiple authors stacking changes onto the same un-deployed-yet migration file — the second author's additions silently get dropped on environments that ran the first version.
