# Booking Flow

This document describes the three booking creation paths: app booking, manual walk-in, and QR walk-in.

---

## 1. App Booking (Customer App)

The customer picks a salon, selects services and a staff member, picks a slot, and books.

```
Customer App                       API                          Database
     │                              │                               │
     │  GET /availability?          │                               │
     │   staff_id=&date=&           │                               │
     │   service_ids=               │                               │
     │ ─────────────────────────── ▶│                               │
     │                              │  get_available_slots(         │
     │                              │    staff_id, date, duration)  │
     │                              │ ─────────────────────────── ▶ │
     │                              │  [{slot_start, slot_end}, …]  │
     │                              │ ◀───────────────────────────  │
     │  [slot_start, slot_end, …]   │                               │
     │ ◀ ───────────────────────── │                               │
     │                              │                               │
     │  POST /bookings              │                               │
     │  {salon_id, staff_id,        │                               │
     │   service_ids, start,        │                               │
     │   source: "app", …}          │                               │
     │ ─────────────────────────── ▶│                               │
     │                              │  create_booking(              │
     │                              │    salon_id, staff_id,        │
     │                              │    services[], start, …)      │
     │                              │ ─────────────────────────── ▶ │
     │                              │  booking_id (UUID)            │
     │                              │ ◀───────────────────────────  │
     │                              │                               │
     │                              │  If approval_mode = "auto"    │
     │                              │  → status = confirmed         │
     │                              │  If approval_mode = "manual"  │
     │                              │  → status = pending           │
     │                              │                               │
     │  BookingResponse (201)       │                               │
     │ ◀ ───────────────────────── │                               │
```

**Slot conflict (409):** If `create_booking` raises because the slot was taken between
availability check and booking, the API returns `{"error": {"code": "slot_unavailable"}}`.
The client must re-fetch availability and prompt the user to choose again.

**Slot timing:** Available slot starts advance by the selected service duration. If the
barber sets a service duration of 30 minutes and working hours are `09:00` to `18:00`,
availability is generated as `09:00-09:30`, `09:30-10:00`, `10:00-10:30`, and so on.
There is no separate slot interval setting exposed to the frontend.

---

## 2. Manual Walk-in (Owner App — no QR)

The owner or staff manually adds a walk-in customer in the owner app.

```
Owner App                          API                          Database
     │                              │                               │
     │  POST /bookings              │                               │
     │  {salon_id, staff_id,        │                               │
     │   service_ids, start,        │                               │
     │   customer_name,             │                               │
     │   customer_phone,            │                               │
     │   source: "manual_walkin"}   │                               │
     │ ─────────────────────────── ▶│                               │
     │                              │  Authorise: role ∈ {owner,    │
     │                              │             staff}            │
     │                              │                               │
     │                              │  create_booking(…,            │
     │                              │    source: "manual_walkin")   │
     │                              │ ─────────────────────────── ▶ │
     │                              │  booking_id                   │
     │                              │ ◀───────────────────────────  │
     │  BookingResponse (201)       │                               │
     │ ◀ ───────────────────────── │                               │
```

Manual walk-in bookings are always auto-confirmed regardless of `approval_mode`.

---

## 3. QR Walk-in (Walk-in App — customer scans QR)

The customer scans the salon's QR code, optionally registers via phone OTP, then books.

```
Customer (Walk-in App)             API                          Database
     │                              │                               │
     │  GET /walkin/{qr_token}      │                               │
     │ ─────────────────────────── ▶│                               │
     │                              │  get_salon_by_qr(qr_token)    │
     │                              │ ─────────────────────────── ▶ │
     │                              │  {salon, services, staff}     │
     │                              │ ◀───────────────────────────  │
     │  WalkInSalonResponse (200)   │                               │
     │ ◀ ───────────────────────── │                               │
     │                              │                               │
     │  POST /walkin/{qr_token}/    │                               │
     │    verify-phone              │                               │
     │  {phone: "+91…"}             │                               │
     │ ─────────────────────────── ▶│                               │
     │                              │  send_phone_otp(phone)        │
     │                              │ ──→ Supabase Auth /otp        │
     │  {verified: false} (200)     │                               │
     │ ◀ ───────────────────────── │                               │
     │                              │                               │
     │  POST /walkin/{qr_token}/    │                               │
     │    verify-phone              │                               │
     │  {phone: "+91…", otp: "…"}   │                               │
     │ ─────────────────────────── ▶│                               │
     │                              │  verify_phone_otp(phone, otp) │
     │                              │ ──→ Supabase Auth /token      │
     │  {verified: true,            │                               │
     │   access_token, …} (200)     │                               │
     │ ◀ ───────────────────────── │                               │
     │                              │                               │
     │  POST /walkin/{qr_token}/    │                               │
     │    bookings                  │                               │
     │  Authorization: Bearer <JWT> │                               │
     │  {staff_id, service_ids,     │                               │
     │   start_datetime}            │                               │
     │ ─────────────────────────── ▶│                               │
     │                              │  create_booking(…,            │
     │                              │    source: "qr_walkin")       │
     │                              │ ─────────────────────────── ▶ │
     │                              │  booking_id                   │
     │                              │ ◀───────────────────────────  │
     │  BookingResponse (201)       │                               │
     │ ◀ ───────────────────────── │                               │
```

---

## Booking Status Lifecycle

```
                    ┌──────────┐
                    │ pending  │◀── approval_mode = manual
                    └────┬─────┘
          approve ◀──────┤────── reject
                         │
                         ▼
                    ┌──────────┐
                    │confirmed │◀── approval_mode = auto
                    └────┬─────┘
          complete ◀─────┤
                         │
                         ▼
                    ┌──────────┐
                    │completed │
                    └──────────┘

    Any non-terminal status → cancel (customer or owner)
    ┌──────────────────────────────────────────────────────┐
    │  cancelled  (terminal)                               │
    └──────────────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────────┐
    │  rejected   (terminal)                               │
    └──────────────────────────────────────────────────────┘
```

---

## Push Notification Triggers

| Status transition | Notification sent to |
|---|---|
| `pending → confirmed` | Customer |
| `pending → rejected` | Customer |
| `confirmed → completed` | Customer |
| `any → cancelled` (by salon) | Customer |
| `any → cancelled` (by customer) | None |
