# Staff services and consecutive visits

Implemented in local source on branch `staff-service-booking`; not deployed. Migration
`0061_staff_service_visits` is prepared for review only. Do not apply it automatically or
bypass the existing migration-policy/evidence gates for the earlier prepared chain.

## Catalog and staff

- `salon_service_categories` gives each salon menu category its own ID. Existing shared
  General subcategory IDs no longer collapse Hair Cutting and Beard Trimming. Legacy
  responses use their displayed labels as a fallback. Public menus include only active
  catalog services assigned to an active professional in the same salon.
- A service's `selection_group="__category__"` makes it an alternative within its menu
  category. `null` permits complementary services. Named groups are scoped to the menu
  category. Both customer selection and database booking writes enforce this rule.
- `POST /v1/salons/me/services/batch` accepts `{services:[ServiceCreateRequest,...]}`
  (1–30). All items commit or roll back together. Owners enter names on separate lines,
  with shared category, price and duration; individual services remain editable.
- `GET/PUT /v1/salons/me/staff/{id}/capabilities` reads/replaces
  `{service_ids:[...],languages:["English","Malayalam"]}` atomically. Languages are
  resolved through the existing reference table and stored on active service assignments.
  Removed services are soft-deactivated; price/duration overrides survive reactivation.
- Public staff include experience, language names, service IDs and effective per-service
  price/duration. No profile IDs, contact details or private working hours are exposed.

## Customer flow

Choose a professional on the services page, then choose from their categories and services.
Their profile (photo, role, experience, languages, services) is available there. Each cart
service retains its own professional; browsing another professional does not reassign it.
Consecutive services with the same professional are grouped, preserving selection order.

The date/time page shows only professionals capable of all services in the relevant
segment. Explicitly changing one refreshes the entire schedule and its server price.
No staff profile is added on that page. Every offered start time fits the complete visit
with immediate handovers; no waiting gaps are offered. Actual completion times remain
estimates. The customer reviews the full timeline before submitting.

## Server contract and concurrency

`POST /v1/availability/visit` accepts `{salon_id,date,segments:[{staff_id,service_ids}]}`.
It delegates to the new `get_available_slots(uuid,date,jsonb,boolean)` overload, returning
start/end, total price and every segment. A secondary handover need not align with that
barber's separate duration-based slot grid; it must fit their actual hours and reservations.

`POST /v1/bookings` retains existing fields and optionally accepts `segments`. The first
staff ID and complete service list must match those segments. The new `create_booking`
overload locks the salon and catalog, validates the whole plan and uses the existing
creator for one parent booking. It snapshots every line, reserves each staff interval,
and records correct service attribution in one transaction. PostgreSQL owns all schedule
and price calculations. Existing single-staff booking and change availability see these
reservations too. Concurrent conflicts roll back everything; retry keys remain actor-scoped.

One parent means one daily Pay at Salon booking, approval, cancellation, no-show decision
and payment. Status changes release every segment together. Staff leave previews match
each actual segment while cancelling the parent once. Owner workload cards use each
professional's segment time, and identify the amount as the complete visit's payment.
The completion action is labelled for the whole visit and shown on the final staff segment.

## Boundaries and release

- Migration execution is bounded by five-second lock acquisition and sixty-second statements.
  Availability and salon-erasure function updates refuse unexpected prior definitions. Legacy
  services without a shared subcategory are included in category backfilling. New tables grant
  backend read/insert/update access; direct delete/truncate and browser access are revoked.
- The existing confirmed admin salon-erasure operation removes visit segments before bookings
  and menu categories after services. Its application lock list includes both new tables.
  Checkout quotes validate the same complete itinerary as booking creation and offer only
  Pay at Salon for segmented visits, even when online payment is enabled elsewhere.
- Multi-professional visits currently support Pay at Salon. Online collection is unchanged.
- The existing single-professional reschedule flow is blocked for multi-professional visits;
  customers are told to contact the salon to arrange the complete schedule. Cancellation
  remains available through the existing whole-booking policy. No client may silently
  flatten a multi-professional visit or alter its reserved staff via earnings attribution.
- Itineraries store service/staff IDs and time/price snapshots, rather than names. Responses
  join current staff names. Historical bookings and segments are retained with the parent;
  existing account erasure continues to anonymize the parent and staff records.
- The existing verified owner-erasure transaction scrubs the new registry label copies
  and custom selection-group text while retaining category/booking identifiers. No remote schema, environment, worker, deployment, store
  submission or installed APK has been changed for this feature.
- Verify native loading, empty/error/offline states, category changes, profiles, alternate
  professionals, cart persistence, final conflict recovery and both themes before release.
  Jest/ASGI/Postgres tests are not native-device layout evidence.
