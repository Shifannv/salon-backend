# Migrations

This folder manages the Supabase Postgres schema — both the full baseline and
incremental Alembic migrations.

---

## Files

```
migrations/
├── 001_supabase_schema.sql   ← Full baseline schema (source of truth)
├── env.py                    ← Alembic async engine config
└── versions/
    ├── 0001_baseline.py      ← Alembic: marks baseline as applied
    └── 0002_notifications_read_at.py  ← Incremental: adds read_at to notifications
```

---

## Fresh Supabase Project Setup

Run `001_supabase_schema.sql` once on an **empty** Supabase project:

1. Open Supabase Dashboard → SQL Editor
2. Paste the full contents of `001_supabase_schema.sql`
3. Run it

The file creates all tables, indexes, triggers, RLS policies, and stored functions
(`create_booking`, `get_available_slots`, `get_salon_by_qr`).

Then run Alembic to stamp the database at the baseline version and apply any
incremental migrations:

```bash
cd backend
alembic upgrade head
```

---

## Adding New Migrations

Never modify the database schema from Python application code.
All schema changes go through Alembic migration files:

```bash
# Create a new migration
alembic revision -m "describe_the_change"

# Apply all pending migrations
alembic upgrade head

# Check current version
alembic current

# Roll back one step
alembic downgrade -1
```

Write the actual SQL inside the `upgrade()` function of the new migration file.
Provide a working `downgrade()` too.

---

## Applied Migrations

| Version | What it does |
|---|---|
| `0001_baseline` | Marks the `001_supabase_schema.sql` schema as the starting point |
| `0002_notifications_read_at` | Adds `read_at timestamptz` column + auto-stamp trigger to `notifications` |

---

## After Initial Setup

Create your first super admin user in Supabase Auth dashboard, then promote them:

```sql
UPDATE profiles
SET role = 'super_admin'
WHERE email = 'you@example.com';
```
