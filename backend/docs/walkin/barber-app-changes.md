# Barber / Owner App — QR Walk-In Changes

## Overview

The owner/barber app needs to:
1. **Display** the salon's unique QR code so it can be printed or shown on a screen
2. **Expose** the QR landing URL for sharing
3. **See** incoming walk-in bookings in the bookings list (they already arrive via `source: "qr_walkin"`)
4. **(Optional Phase 2)** Rotate the QR token if needed (e.g. after a security incident)

---

## New Screen: QR Code Screen

### Location in Navigation
```
Bottom Tab: Home / Bookings / QR / Staff / Settings
                              ^^^
                         New tab icon: qr-code-outline (Ionicons)
```

Or as a nested screen accessible from **Settings → Walk-In QR Code**.

---

### Screen: `QRCodeScreen.tsx`

**What it does:**
- Calls `GET /v1/salons/me` → gets `qr_token` from the owner salon response
- Constructs the walk-in URL: `https://walkin.yourdomain.com/s/{qr_token}`
- Renders the QR code as a visual using `react-native-qrcode-svg`
- Shows the URL as copyable text
- "Share" button → `Share.share({ url, message })` (React Native Share API)
- "Download / Print" → opens URL in browser for printing on web

**Data needed from backend:**
```
GET /v1/salons/me   (existing, owner-authenticated)
→ OwnerSalonResponse { ..., qr_token: string }
```

> ⚠️ **Backend change required**: `qr_token` must be added to `OwnerSalonResponse`.
> It is already stored in the `salons` table but is not currently included in the schema response.

---

### UI Layout

```
┌─────────────────────────────────┐
│  ←  Walk-In QR Code             │
├─────────────────────────────────┤
│                                 │
│   📍 Scissors & Co., Chennai   │
│                                 │
│   ┌─────────────────────────┐   │
│   │                         │   │
│   │   ████ QR CODE ████     │   │
│   │   ████          ████    │   │
│   │   ████          ████    │   │
│   │   ████ ████ ████ ████   │   │
│   │                         │   │
│   └─────────────────────────┘   │
│                                 │
│   walkin.salonapp.com/s/a3f8...  │
│   [Copy Link]  [Share]          │
│                                 │
│   ┌─────────────────────────┐   │
│   │ 💡 Customers scan this  │   │
│   │    to book instantly.   │   │
│   │    No app needed.       │   │
│   └─────────────────────────┘   │
│                                 │
│   [Rotate QR (if compromised)]  │
│                                 │
└─────────────────────────────────┘
```

---

### Dependencies to Add

```bash
# In the barber app repo
npx expo install react-native-qrcode-svg
npx expo install react-native-svg  # peer dependency
```

### Sample Component

```tsx
import QRCode from 'react-native-qrcode-svg';
import { Share } from 'react-native';

const WALKIN_BASE = 'https://walkin.salonapp.com/s';

export function QRCodeScreen() {
  const { salon } = useOwnerSalon(); // hook calling GET /v1/salons/me
  const walkinUrl = `${WALKIN_BASE}/${salon?.qr_token}`;

  const handleShare = () => Share.share({ url: walkinUrl, message: `Book at ${salon?.name}: ${walkinUrl}` });

  return (
    <SafeAreaView>
      <Text>{salon?.name}</Text>
      {salon?.qr_token && <QRCode value={walkinUrl} size={240} />}
      <Text selectable>{walkinUrl}</Text>
      <Button title="Share" onPress={handleShare} />
      <Button title="Rotate QR" onPress={handleRotateQr} />
    </SafeAreaView>
  );
}
```

---

## Walk-In Bookings in Bookings List

Walk-in bookings already appear in `GET /v1/bookings` because the owner sees all bookings for their salon. No backend change needed.

**Recommended UI enhancement**: Add a badge/label on walk-in bookings so the barber immediately recognises them:

```tsx
// In BookingCard.tsx — add a source badge
{booking.source === 'qr_walkin' && (
  <Badge label="Walk-In QR" variant="purple" />
)}
{booking.source === 'manual_walkin' && (
  <Badge label="Walk-In Manual" variant="blue" />
)}
```

The `source` field is already returned in `BookingResponse`.

---

## Walk-In Toggle (Phase 2 — Optional)

Allow the owner to pause walk-in bookings (e.g. salon fully booked):

```
Settings → Walk-In Bookings [Toggle ON/OFF]
```

**Backend change needed**: A `walkin_enabled: bool` column on `salons` table, and the `get_salon_by_qr` function would return 404 (or a "paused" status) when disabled.

This is a Phase 2 feature — do not build in Phase 1.

---

## Summary of Changes

| Change | Type | Priority |
|---|---|---|
| New `QRCodeScreen` screen | Frontend | **Phase 1** |
| Add QR tab or Settings entry point | Frontend | **Phase 1** |
| Install `react-native-qrcode-svg` | Dependency | **Phase 1** |
| Add `qr_token` to `OwnerSalonResponse` | Backend schema | **Phase 1** |
| Walk-in source badge in BookingCard | Frontend | **Phase 1** |
| QR rotate endpoint | Backend | Phase 2 |
| Walk-in toggle (pause/enable) | Backend + Frontend | Phase 2 |
