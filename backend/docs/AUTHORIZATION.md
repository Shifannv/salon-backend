# Authorization Mapping

The SQL schema has RLS enabled, but the API connects through one privileged
Postgres role (the service role). Every RLS policy is therefore mirrored as
an explicit authorization check in the application layer.

---

## RLS Policy → Use-Case Guard Table

| Schema policy intent | Application guard | Code location |
|---|---|---|
| Active authenticated user can read self | `GetMe` resolves JWT `sub` to `profiles.id` and rejects inactive profiles | `api/deps.py → get_current_actor` |
| Super-admin creates salon owners | `require_role(Role.super_admin)` dependency | `routes/admin.py` |
| Super-admin updates/deactivates salons | `require_role(Role.super_admin)` dependency | `routes/admin.py` |
| Super-admin manages catalog (categories/subcategories/languages) | `require_role(Role.super_admin)` dependency | `routes/admin.py` |
| Owner owns salon — read | `OwnerUseCases._assert_owner_workspace` → `is_owner_or_staff(actor)` | `use_cases/platform.py` |
| Owner owns salon — write | `OwnerUseCases._assert_owner_workspace` + `get_owner_salon(actor_id)` checks `owner_id = actor_id` in SQL | `platform_repository.py` |
| Owner owns images, holidays, services, staff | All write queries join through `get_owner_salon(actor_id)` which scopes to `owner_id = actor_id` | `platform_repository.py` |
| Staff belongs to owner salon | `assign_staff_service` checks `st.salon_id = :salon_id` | `platform_repository.py` |
| Staff service language belongs to owner | `set_staff_service_languages` verifies `st.salon_id = :salon_id` before deleting/inserting | `platform_repository.py` |
| Blocked slot belongs to owner salon | `create_blocked_slot` / `delete_blocked_slot` scope to `salon_id` from `get_owner_salon` | `platform_repository.py` |
| Customer sees only own bookings | `list_bookings(role="customer")` → `customer_id = :actor_id` | `platform_repository.py` |
| Owner sees only their salon bookings | `list_bookings(role="owner")` → `owner_id = :actor_id` via subquery | `platform_repository.py` |
| Customer can only cancel own booking | `cancel(customer_only=True)` → `customer_id = :actor_id` predicate | `platform_repository.py` |
| Customer owns notification | `mark_notification_read` → `user_id = :actor_id` predicate | `platform_repository.py` |
| Device token belongs to actor | `register_device(actor_id)` / `deactivate_device_for_actor(actor_id)` | `platform_repository.py` |
| Walk-in is unauthenticated but salon must be active | `get_salon_by_qr` calls `get_salon_by_qr` Postgres fn which checks `is_active` | `platform_repository.py` |

---

## How to Extend

Before adding a new feature:

1. Read the `-- ROW LEVEL SECURITY` section in `migrations/001_supabase_schema.sql`.
2. Identify which RLS policies apply to the new resource.
3. Add the corresponding use-case guard to the table above.
4. Implement the guard in the application use case (not the router or repository).
5. Update this table in the same PR.

> **Rule:** Authorization must never live in routers or repositories.
> Routers authenticate. Use cases authorize. Repositories access data.
