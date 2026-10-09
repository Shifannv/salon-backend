
## Discovery ranking (migration `0017_salon_display_priority`)

Super admins control public ordering with `salons.display_priority`
(integer, `0..100000`, default `0`, higher ranks first). This is **manual
control only**: it is not derived from subscriptions, and the repository has no
subscription or billing source today. If one is added, a separate tier-to-priority
rule must first verify subscription status, tier, active period, cancellation or
expiry, tie-breaking, and billing privacy.

- Admin: `PATCH /v1/admin/salons/{salon_id}` accepts `display_priority` (strict
  integer, `0..100000`). The response (and admin list/detail) returns
  `display_priority` and `updated_by`; `updated_at`/`updated_by` are stamped by
  the existing audit trigger. Owners cannot set it: the admin route requires
  `super_admin` and a database trigger rejects non-admin changes.
- Public: visibility (`approved`, active, profile completed) is applied first,
  then `display_priority DESC, distance_km ASC NULLS LAST, name ASC, id ASC`
  before pagination, for `/v1/salons` (home, search, category, favorites) and
  `/v1/salons/nearby`. The value is not returned to customers; the list order is
  the contract. Discovery lists are not cached; if they ever are, invalidate them
  when `display_priority` changes.
