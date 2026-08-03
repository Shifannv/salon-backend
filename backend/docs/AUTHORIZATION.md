# Authorization Mapping

The SQL schema keeps RLS enabled, but the API connects through one privileged Postgres
role. Every RLS policy must therefore be mirrored in use-case authorization checks.

Status: Phase 1 foundation only.

| Schema policy intent | Application guard |
| --- | --- |
| Active authenticated user can read self | `GetMe` resolves JWT `sub` to `profiles.id` and rejects inactive profiles |
| Super admin checks | `domain.services.authorization.is_super_admin` |
| Owner owns salon checks | Pending Phase 2/3 use cases |
| Customer sees only own bookings | Pending Phase 4 booking use cases |
| Super admin writes catalog | Pending Phase 2 catalog use cases |
| Device token belongs to actor | Pending Phase 6 notification use cases |

Before building each phase, read the `-- ROW LEVEL SECURITY` section in
`migrations/001_supabase_schema.sql` and extend this table with exact policy-to-use-case
mappings.
