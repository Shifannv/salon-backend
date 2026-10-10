
## Discovery ranking (migration `0017_salon_display_priority`)

Super admins control public ordering with `salons.display_priority`
(integer, `0..100000`, default `0`, higher ranks first). Migration `0018` also
adds subscription promotion weights for eligible, manually activated subscriptions.
Paid checkout and verified payment webhooks remain absent.

- Admin: `PATCH /v1/admin/salons/{salon_id}` accepts `display_priority` (strict
  integer, `0..100000`). The response (and admin list/detail) returns
  `display_priority` and `updated_by`; `updated_at`/`updated_by` are stamped by
  the existing audit trigger. Owners cannot set it: the admin route requires
  `super_admin` and a database trigger rejects non-admin changes.
- Public: approval, activity, completion and discovery visibility apply before
  pagination. Eligible subscription weight precedes numeric priority, distance,
  name and ID. The home surface additionally groups top, normal, random and below;
  the random group uses a stable shuffle seed. Search/nearby do not use home placement.
  The values are not returned to customers; list order is the contract.

Migration `0019_discovery_placement` adds `discovery_visibility` (listed, search_only,
hidden) and `home_placement` (top, normal, below, random), both super-admin-only.
Discovery hiding leaves approved direct details/QR accessible; it does not suspend
the owner. See the [approval workflow](../backend/docs/SALON_APPROVAL.md) and
[website prompt](../backend/docs/WEBSITE_SUPERADMIN_PROMPT.md) for current contracts.
