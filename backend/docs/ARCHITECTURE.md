# Architecture

The FastAPI service is the shared API layer between the client apps and Supabase.

```txt
api -> application -> domain
infrastructure -> domain/application ports
```

Rules:

- Routers validate HTTP, authenticate actors, and wire dependencies.
- Use cases own authorization and business flow.
- Repositories are data access adapters only.
- `domain/` has no FastAPI, SQLAlchemy, Supabase, or Pydantic HTTP schemas.
- Bookings must call the Postgres `create_booking` function.
- Availability must call the Postgres `get_available_slots` function.

The old compact router/service implementation is not considered compliant with the new
architecture because it used sync SQLAlchemy, local password tokens, Python slot
calculation, and Python booking inserts.
