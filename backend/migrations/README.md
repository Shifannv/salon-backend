# Supabase Migrations

This folder contains SQL migrations for the Supabase PostgreSQL database.

## Files

```txt
001_supabase_schema.sql
```

This file is the full platform schema from the prompt text you provided.

It includes:

- PostgreSQL extensions
- enums
- tables
- indexes
- triggers
- Supabase Auth profile trigger
- RLS helper functions
- RLS policies
- slot engine RPC
- booking creation RPC
- QR lookup RPC

## Important

Run `001_supabase_schema.sql` only on an empty Supabase project.

The file itself says:

```txt
Run top to bottom on an EMPTY Supabase project.
```

If your Supabase database already has older versions of these tables, do not run this full migration directly. Use incremental migration files instead.

## Apply Through Supabase Dashboard

1. Open Supabase Dashboard.
2. Select your project.
3. Go to SQL Editor.
4. Open `001_supabase_schema.sql`.
5. Copy the full file content.
6. Paste it into SQL Editor.
7. Run it.

## Apply Through Supabase CLI

If you use Supabase CLI, copy this file into the Supabase migrations folder with a timestamped filename.

Example:

```txt
supabase/migrations/20260731000100_initial_schema.sql
```

Then run:

```bash
supabase db push
```

## After Applying

Create your first super admin user in Supabase Auth, then promote that user:

```sql
update profiles
set role = 'super_admin'
where email = 'you@example.com';
```

Replace `you@example.com` with your real admin email.

