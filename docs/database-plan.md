# Database Plan

## Backend Platform

The backend/database will use Supabase.

Supabase will handle:

- Authentication
- PostgreSQL database
- Row-level security
- Customer data
- Salon data
- Booking data
- Notification data

## Main Tables

### profiles

Stores customer profile information.

Suggested fields:

```txt
id
user_id
full_name
phone
avatar_url
created_at
updated_at
```

Notes:

- `user_id` should link to Supabase Auth user.
- Customer should only read/update their own profile.

### salons

Stores salon information.

Suggested fields:

```txt
id
name
description
address
city
latitude
longitude
phone
image_url
rating
is_active
created_at
updated_at
```

Notes:

- `latitude` and `longitude` are needed for nearby salon search.
- Customer app should only show active salons.

### service_categories

Stores service categories.

Suggested fields:

```txt
id
name
description
created_at
updated_at
```

Examples:

- Hair
- Beard
- Facial
- Spa
- Bridal

### services

Stores salon services.

Suggested fields:

```txt
id
salon_id
category_id
name
description
price
duration_minutes
is_active
created_at
updated_at
```

Notes:

- A salon can have many services.
- A service belongs to one salon.

### bookings

Stores customer booking records.

Suggested fields:

```txt
id
customer_id
salon_id
service_id
booking_date
start_time
end_time
status
notes
created_at
updated_at
```

Possible status values:

```txt
pending
confirmed
cancelled
completed
rejected
```

Notes:

- Customer should only read their own bookings.
- Backend should prevent double booking for the same salon/service/time if required.

### notifications

Stores notification records shown inside the app.

Suggested fields:

```txt
id
customer_id
title
message
type
is_read
booking_id
created_at
updated_at
```

Possible notification types:

```txt
booking_created
booking_cancelled
booking_reminder
general
```

### device_tokens

Stores Firebase/FCM device tokens for push notifications.

Suggested fields:

```txt
id
customer_id
fcm_token
platform
is_active
created_at
updated_at
```

Possible platform values:

```txt
android
ios
```

## Relationships

```txt
profiles.user_id -> auth.users.id
services.salon_id -> salons.id
services.category_id -> service_categories.id
bookings.customer_id -> profiles.id
bookings.salon_id -> salons.id
bookings.service_id -> services.id
notifications.customer_id -> profiles.id
notifications.booking_id -> bookings.id
device_tokens.customer_id -> profiles.id
```

## Row-Level Security Notes

Use Supabase RLS policies to protect customer data.

Customers should be able to:

- Read active salons
- Read active services
- Read their own profile
- Update their own profile
- Create their own bookings
- Read their own bookings
- Cancel their own eligible bookings
- Read their own notifications
- Update read status on their own notifications
- Create/update their own device token

Customers should not be able to:

- Read another customer's profile
- Read another customer's bookings
- Update salon data
- Update service data
- Read another customer's notifications

## Location Query

Nearby salon discovery should use:

```txt
customer latitude
customer longitude
salon latitude
salon longitude
```

Expected backend result:

```txt
salon id
salon name
image url
address
rating
distance in km
starting price
```

