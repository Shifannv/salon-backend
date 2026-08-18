# QR Walk-In Booking Web App — Architecture

## Overview

A lightweight, mobile-first web app that customers reach by **scanning a salon's QR code**. No app install required. The customer sees the salon, picks a service, verifies via phone OTP, and is booked in under 60 seconds.

```
QR Code → https://walkin.yourdomain.com/s/{qr_token}
```

The `qr_token` is a 32-character hex string stored in the `salons` table. It never changes unless explicitly rotated by the owner.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | **Next.js 14 (App Router)** | SSR for instant first load on mobile, easy Vercel deploy |
| Styling | **Tailwind CSS** | Utility-first, tiny bundle, fast to build |
| State | **React useState + useReducer** | No Redux needed — linear 3-step flow |
| HTTP | **native fetch** | No dependencies; calls the shared FastAPI backend |
| Database | **Same Supabase project as the app** | No new DB — all data in one place |
| Auth / OTP | **Same Supabase Auth project as the app** | Phone OTP via Supabase — walk-in users become real profiles |
| OTP UI | Custom 6-box input component | Match native SMS OTP feel on mobile |
| Deploy | **Vercel** | Zero-config Next.js, global CDN, env vars UI |

---

## Database & Auth — Same Supabase Project

The walk-in web app does **not** use a separate database or auth service.
It is just another client of the **same shared backend** that the customer app and barber app already use.

```
┌─────────────────────────────────────────────────────────┐
│                  Shared Infrastructure                  │
│                                                         │
│   ┌───────────────────────────────────────────────┐    │
│   │           FastAPI Backend (shared API)         │    │
│   └───────────────────┬───────────────────────────┘    │
│                       │                                 │
│   ┌───────────────────▼───────────────────────────┐    │
│   │    Supabase Postgres  +  Supabase Auth         │    │
│   │    (same project, same tables, same users)     │    │
│   └───────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
         ▲                  ▲                  ▲
         │                  │                  │
  Customer App        Barber App        Walk-In Web
  (React Native)    (React Native)      (Next.js)
```

### What this means in practice

| Concern | Result |
|---|---|
| Walk-in bookings | Written to the **same `bookings` table** — barber sees them instantly |
| Walk-in customer profiles | Created as real `profiles` rows with `role = customer` |
| Phone OTP | Same Supabase Auth project — same SMS provider, same usage quota |
| No duplicate data | One source of truth — no sync job needed |
| Barber app sees walk-ins | `source = 'qr_walkin'` flag distinguishes them in the list |

### Environment variables for the web app

```bash
# .env.local (walk-in web)
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com   # same FastAPI backend URL
```

> The web app **never calls Supabase directly**. All database reads and writes go through the FastAPI backend, exactly like the mobile apps. The Supabase anon key is never exposed to the web client.

---

## URL Scheme

```
https://walkin.yourdomain.com/s/{qr_token}
```

The entire site is a **single dynamic route**: `app/s/[qrToken]/page.tsx`

---

## Page Flow (3 Steps — slots-first, no salon detail page)

On QR scan the customer lands **directly on the time slot picker**. The salon name appears only as a small header label — no dedicated salon info page.

```
Step 0  LOADING
         ↓ Fetch salon + services + staff in parallel
         ↓ Auto-select: first available staff + today's date
         ↓ Fetch today's slots immediately
         ↓
Step 1  SLOT PICKER                   ← public, no auth
         ┌──────────────────────────┐
         │  ✂ Scissors & Co         │  ← small salon name only
         │  Chennai                 │
         ├──────────────────────────┤
         │  [Service chips row]     │  ← tap to change service
         │  Haircut ▼               │  (collapsed pill, not a full list)
         ├──────────────────────────┤
         │  [Staff chips row]       │  ← optional barber pick (or "Any")
         ├──────────────────────────┤
         │  [Date selector strip]   │  ← today / tomorrow / day after
         ├──────────────────────────┤
         │  TIME SLOTS              │
         │  ◉ 10:00 AM  ○ 10:30 AM │
         │  ○ 11:00 AM  ○ 11:30 AM │
         │  ...                     │
         ├──────────────────────────┤
         │  [Book This Slot →]      │
         └──────────────────────────┘
         ↓
Step 2  PHONE VERIFY
         Enter +91XXXXXXXXXX → OTP sent
         Enter 6-digit OTP → returns JWT
         Enter name (first + last)
         ↓
Step 3  SUCCESS
         ✅ Booking confirmed
         Booking ref, date, time, barber name
         "Add to Calendar" link
```

### Fast-Book shortcut
If the customer does not interact at all (default auto-selection):
- **Service** = first in the list
- **Staff** = first available barber today
- **Slot** = next open slot

They can tap "Book This Slot" in seconds with zero configuration.

---

## Project Structure

```
walkin-web/
├── app/
│   ├── layout.tsx                  # Root layout, global fonts, meta
│   ├── s/
│   │   └── [qrToken]/
│   │       └── page.tsx            # Fetches salon + slots → renders 3-step flow
│   └── not-found.tsx               # Invalid QR or inactive salon
├── components/
│   ├── SlotBookingPage.tsx         # ROOT: salon mini-header + all step content
│   ├── SalonMiniHeader.tsx         # Tiny header: salon name + city only (not a page)
│   ├── ServiceChipBar.tsx          # Collapsed horizontal chip row (tap to change service)
│   ├── StaffChipBar.tsx            # "Any" + barber chips horizontal row
│   ├── DateStripPicker.tsx         # Today / Tomorrow / +2 day strip
│   ├── SlotGrid.tsx                # Time slot chip grid (the main content on landing)
│   ├── PhoneVerifyStep.tsx         # Phone input → OTP input → name input
│   ├── SuccessScreen.tsx           # Booking confirmed screen
│   └── ui/
│       ├── Button.tsx
│       ├── OtpInput.tsx            # 6-box SMS code input
│       ├── Spinner.tsx
│       ├── ChipSelect.tsx          # Reusable horizontal chip row
│       └── ErrorBanner.tsx
├── lib/
│   ├── api.ts                      # Typed fetch wrappers for all API calls
│   ├── types.ts                    # WalkInSalon, Service, Staff, Slot, Booking
│   ├── autoSelect.ts               # findNextAvailable() — picks staff+slot for fast-book
│   └── formatters.ts               # Price, duration, time display helpers
├── .env.local
├── next.config.ts
└── tailwind.config.ts
```

---

## API Calls (all to the existing backend — no new endpoints needed)

### On Page Load — Parallel fetch (no user action required)
```
① GET /v1/walkin/{qr_token}
   → { id, name, city, services[], staff[] }
   Auto-select: service = services[0], staff = staff[0]

② GET /v1/availability?staff_id={staff[0].id}&date={today}&service_ids[]={services[0].id}
   → [ { id, time, barberName, slot_start, slot_end } ]
   Customer lands on the slot grid immediately — no taps needed yet.
```

### When customer changes service / staff / date — refetch slots
```
GET /v1/availability?staff_id={selected_staff_id}&date={selected_date}&service_ids[]={selected_service_id}
→ Updated slot grid (show loading spinner inline, not full-page)
```

### Step 2 — Phone OTP (fires when customer taps "Book This Slot")
```
POST /v1/walkin/{qr_token}/verify-phone
Body: { "phone": "+919876543210" }
→ { "verified": false }

POST /v1/walkin/{qr_token}/verify-phone
Body: { "phone": "+919876543210", "otp": "123456" }
→ { "verified": true, "access_token": "...", "refresh_token": "..." }
```

### Step 3 — Get Available Slots (public)
```
GET /v1/availability?staff_id={id}&date={YYYY-MM-DD}&service_ids[]={id}
→ [ { id, time, barberName, slot_start, slot_end } ]
```
> **"Next available"** = first slot in the response (sorted by slot_start ascending)

### Step 4 — Create Booking (requires JWT from Step 2)
```
POST /v1/walkin/{qr_token}/bookings
Authorization: Bearer {access_token}
Body: {
  "salon_id":       "uuid",
  "staff_id":       "uuid",
  "service_ids":    ["uuid"],
  "start_datetime": "2026-08-06T10:00:00",
  "customer_name":  "Rahul",
  "customer_phone": "+919876543210"
}
→ BookingResponse { id, status: "confirmed", ... }
```

---

## Fast-Book Logic (Auto-Select Next Available)

```typescript
async function findNextAvailable(staff: Staff[], serviceIds: string[]) {
  const today = new Date().toISOString().slice(0, 10);
  for (const barber of staff) {
    const slots = await getAvailability(barber.id, today, serviceIds);
    if (slots.length > 0) return { barber, slot: slots[0] };
  }
  return null; // fully booked today
}
```

When the customer taps "Book Next Available":
1. Loop through staff in order returned by the backend
2. Call availability for each
3. Pre-fill the booking form with the first result found
4. Customer just enters their name → phone → OTP → confirm

---

## Deployment

```bash
npx create-next-app@latest walkin-web --typescript --tailwind --app
cd walkin-web

# .env.local
echo "NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com" > .env.local

# Deploy to Vercel
vercel --prod
```

Add the Vercel domain to the FastAPI CORS allowed origins list.

---

## What Does NOT Need to Change in Backend

| Item | Status |
|---|---|
| `salons.qr_token` column | ✅ Already exists |
| `GET /v1/walkin/{token}` | ✅ Already exists (public) |
| `POST /v1/walkin/{token}/verify-phone` | ✅ Already exists |
| `POST /v1/walkin/{token}/bookings` | ✅ Already exists |
| `GET /v1/availability` | ✅ Already public |
| `source: "qr_walkin"` tracking | ✅ Already in DB schema |
