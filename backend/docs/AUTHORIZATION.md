# Authorization

Clients send Supabase access tokens as bearer tokens. The backend verifies each token
against Supabase JWKS, uses the verified `sub` to load `profiles.id`, and reads the role
from the database. JWT role claims are not trusted.

Authorization belongs in application use cases:

- customers access their own profile, bookings, notifications, and reports;
- owners access the salon workspace they own and may also use customer flows;
- staff access only operations explicitly allowed for their salon;
- super admins manage platform-wide salon and catalog records.

Repository queries must still scope reads and writes by actor or owned resource, but
repositories do not decide policy. RLS stays enabled as defense in depth.

Authenticated transactions set:

```sql
SET LOCAL request.jwt.claims = '{"sub": "<verified-user-uuid>"}';
```

This allows database audit triggers to record the verified actor.

Payment recording and booking-delay updates remain owner/staff operations. Customer
payment confirmation requires a verified payment-provider flow and must not be granted
by trusting a client request.
