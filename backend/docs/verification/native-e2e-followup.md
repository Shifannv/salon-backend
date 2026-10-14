# Native verification follow-up — 2026-10-14

The resumed checkout still contained the unfixed customer instant-rebook query cycle after the backend changes were merged in PR #52. Claims below distinguish implementation checks, device actions and remaining failures.

## Completed and verified

- Customer real-component regression: old code performed 30 salon-detail reads rather than one. The sheet now receives booking eligibility from its parent's verified detail query. The same regression settles at one, including when the salon has paused bookings. No backend authorization or live eligibility check was removed.
- Native AppState duplicate notifications no longer clear salon caches. Real background/foreground transitions still refresh them.
- Customer device navigated Home -> Services -> Select Date & Time -> Review -> Booking Approved using localhost-only API/Auth and real disposable PostgreSQL. Backend creation returned 201 with request ID 65ccfd50636646978991d65291ddd740.
- Database booking bbcbd348-72b7-4f35-acdc-074abd6d598e: app source, October 15 09:00 IST, confirmed, unpaid, INR 250.00, one service row and one booking audit event. Read verification is stored locally in `.artifacts/latency-native-database-state.json`.
- Owner device retrieved the earlier real-browser synthetic booking d871419a-46f3-4b1a-ae33-f383c4084519 and recorded cash through POST /bookings/{id}/payment (200). PostgreSQL independently verified paid/cash state, exactly one manual captured INR 250.00 receipt, and two booking audit events. This is a synthetic manual ledger entry, with no real funds or payment-provider call. Evidence: `.artifacts/latency-owner-device-database-state.json`.
- Earlier October 14 attempt returned 409 pay_at_salon_daily_limit because the browser test had already booked that day. Another date succeeded. The UI recovery message was improved without changing the limit.
- Customer targeted suites: 21 passed; customer TypeScript check passed with a sufficient heap. Owner checkout/repository/local-network suites: 36 passed. Owner preference values now match the backend checkout contract and still reject unknown values; ownership validation remains active. The live owner booking response (62 rows) also passed the corrected validator.
- Browser regression and real-local browser booking evidence remain as documented in the latency report. All business writes were synthetic.
- Final clean owner test bundle was signed, installed and cold-launched after temporary query diagnostics were removed. Its current process remained foreground with zero fatal/mounting/booking-TypeError markers at the bounded startup check; the separately reproduced calendar crash remains open.

## Changed frontend files

Customer repository (`Salon-Customer-APP/customer-app`):

- `src/components/booking/InstantRebookButton.tsx`, `InstantBookingSheet.tsx`: one owner for the verified salon-detail query, avoiding recursive refetch on child mount.
- `src/server-state/queryClient.ts`: ignore duplicate AppState values.
- `src/utils/customerError.ts`: safe recovery for the actual daily-limit response.
- Focused tests for instant rebooking, AppState, open hours, booking review and error copy; review assertions updated to the currently implemented salon payment-options contract.
- `src/test/test-utils.tsx`: stable test query client and no test GC timers.
- Separate localhost-only `local-e2e-entry.tsx`; normal production auth entry remains unchanged. The ineffective Reanimated 4.5.4 upgrade experiment was reverted to the original Expo-matched 4.5.1. `scripts/patch-reanimated-view-lifetime.cjs` and its postinstall hook add a version-guarded view-existence check to the RN 0.86 reflection path, matching React Native's existing lifetime check. Updates to detached view tags are skipped; real update errors retain logging and animations remain enabled. The final native build succeeded and services-to-date/time navigation produced zero mounting/prop-update error markers in the fresh app process.

Owner repository (`salon-owner-APP`):

- `src/lib/validation/booking.schema.ts`, `src/api/contract.ts`: distinguish checkout preference from a collected payment method, retaining legacy responses and strict validation.
- `src/features/bookings/screens/BookingsScreen.tsx`: label pay-at-salon/advance/full intent correctly.
- `src/lib/validation/booking-checkout.test.ts`: valid current and legacy preferences plus unknown-value rejection.
- `src/lib/query-client.ts` and tests: localhost API reads can execute over ADB when Android internet detection reports offline; remote network behavior is unchanged.
- `src/api/repositories/booking.repository.ts`: explicit promise mapping for the validated page. Android's earlier awaited-page dereference raised a TypeError at line 43; the explicit mapping settled real device queries with one current-day row and 62 overall, then manual cash recording succeeded. The exact compiler/runtime reason for the differing behavior is not established. No empty fallback or skipped validation was added.
- Separate localhost-only E2E entry signs in using the synthetic Auth fixture; the normal Google/provider flow was not changed or verified.

## Still requires verification or repair

- The final customer guard build passed the reproduced services/date-time navigation with zero error markers; this is a bounded device run, not proof that every native screen is error-free.
- The owner API list TypeError is fixed and manual device collection passed with database verification. The owner calendar still crashes during a later calendar transition with a native Yoga ownership assertion, even after the fresh rebuild. This remains open; the working current-day feed was used for collection. No calendar redesign or animation removal was performed. Per the user's clarified scope, visual UI work remains with the user; this native navigation crash must not be described as fully resolved.
- Owner full TypeScript check reports 16 existing marketplace-field schema-test errors (masking/discount metadata absent from the validator). The targeted contract tests pass; the full owner check does not. No backend marketplace feature was invented to hide this mismatch.
- Five opt-in backend tests failed when explicitly enabled; all fourteen names, risks and unskip plans are in the latency report. They are not passing simply because the ordinary run skips them.
- No independent staging URL/environment, hosted Google Auth flow, real provider payment, or email delivery was verified. Remote DB health still misses its 100 ms target.
- The merged backend PR included pytest temporary files. Their already-deleted working-tree state is preserved and `.gitignore` now excludes `backend/.pytest_tmp/` to prevent recurrence; no deletion of application data is involved.

The exact existing screenshot request cannot be retrospectively traced. The reproducible latency evidence and before/after distributions are in [latency-investigation.md](latency-investigation.md) and [latency-measurements.json](latency-measurements.json).
