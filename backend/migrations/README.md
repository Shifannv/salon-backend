# Database migrations

Alembic owns the complete schema history.

- `001_supabase_schema.sql` is the raw SQL baseline.
- `versions/0001_baseline.py` applies that baseline to an empty database.
- Later revisions add schema required by the current application.
- `versions/0011_holiday_soft_delete.py` adds safe holiday deactivation.
- `versions/0012_booking_delay.py` stores operational delay estimates.
- `versions/0013_booking_action_requests.py` adds action requests, Pay at Salon
  preference, retryable notification outbox records, and closure race protection.
- `versions/0014_repair_cancel_reason.py` restores the nullable booking
  cancellation reason column on databases whose recorded revision reached `0013`
  without the column. Its downgrade leaves the column owned by revision `0009`.

For a new empty database, run only:

```bash
cd backend
alembic upgrade head
```

Do not paste the baseline into Supabase and then run revision `0001`; that would apply
the same schema twice. If a database was created manually from the baseline before
Alembic tracking was introduced, verify its schema, then use:

```bash
alembic stamp 0001_baseline
alembic upgrade head
```

Useful commands:

```bash
alembic current
alembic history
alembic heads
alembic revision -m "describe_change"
alembic upgrade head
alembic downgrade -1
```

Never edit or delete a revision already applied to a shared environment. Add a new,
reviewed revision with both upgrade and downgrade behavior. Migrations remain an
explicit deployment step and never run during API startup.
