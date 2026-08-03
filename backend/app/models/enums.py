from enum import StrEnum


class UserRole(StrEnum):
    super_admin = "super_admin"
    owner = "owner"
    staff = "staff"
    customer = "customer"


class ApprovalMode(StrEnum):
    auto = "auto"
    manual = "manual"


class BookingStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"
    completed = "completed"
    cancelled = "cancelled"


class PaymentStatus(StrEnum):
    unpaid = "unpaid"
    paid = "paid"


class PaymentMethod(StrEnum):
    cash = "cash"
    online = "online"


class BookingSource(StrEnum):
    app = "app"
    manual_walkin = "manual_walkin"
    qr_walkin = "qr_walkin"

