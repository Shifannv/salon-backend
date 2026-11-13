"""Raw SQL repository adapter for frontend-facing platform APIs.

The implementation lives in ``platform/`` (one mixin per area); this module keeps the
original import path and composes the mixins into ``PlatformRepository``.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.platform._sql import (
    _BUSINESS_ERROR_SQLSTATES,
    SqlHelpersMixin,
    _canonical_json_value,
    _contains_pattern,
    _is_business_error,
    _request_fingerprint,
)
from app.infrastructure.db.repositories.platform.admin_salon_erasure import AdminSalonErasureMixin
from app.infrastructure.db.repositories.platform.admin_salons import AdminSalonsMixin
from app.infrastructure.db.repositories.platform.booking_action_requests import (
    BookingActionRequestsMixin,
)
from app.infrastructure.db.repositories.platform.booking_create import BookingCreateMixin
from app.infrastructure.db.repositories.platform.booking_payments import BookingPaymentsMixin
from app.infrastructure.db.repositories.platform.booking_queries import BookingQueriesMixin
from app.infrastructure.db.repositories.platform.booking_updates import BookingUpdatesMixin
from app.infrastructure.db.repositories.platform.categories import CategoriesMixin
from app.infrastructure.db.repositories.platform.closures import ClosuresMixin
from app.infrastructure.db.repositories.platform.languages_slots import LanguagesSlotsMixin
from app.infrastructure.db.repositories.platform.media_refs import MediaRefsMixin
from app.infrastructure.db.repositories.platform.no_show_warnings import NoShowWarningsMixin
from app.infrastructure.db.repositories.platform.notification_outbox import NotificationOutboxMixin
from app.infrastructure.db.repositories.platform.notifications_devices import (
    NotificationsDevicesMixin,
)
from app.infrastructure.db.repositories.platform.owner_catalog import OwnerCatalogMixin
from app.infrastructure.db.repositories.platform.owner_salon import OwnerSalonMixin
from app.infrastructure.db.repositories.platform.payouts import PayoutsMixin
from app.infrastructure.db.repositories.platform.profiles import ProfilesMixin
from app.infrastructure.db.repositories.platform.public_catalog import PublicCatalogMixin
from app.infrastructure.db.repositories.platform.walkin import WalkinMixin

__all__ = [
    "_BUSINESS_ERROR_SQLSTATES",
    "PlatformRepository",
    "_canonical_json_value",
    "_contains_pattern",
    "_is_business_error",
    "_request_fingerprint",
]


class PlatformRepository(
    SqlHelpersMixin,
    MediaRefsMixin,
    ProfilesMixin,
    PublicCatalogMixin,
    OwnerSalonMixin,
    PayoutsMixin,
    OwnerCatalogMixin,
    LanguagesSlotsMixin,
    BookingCreateMixin,
    BookingQueriesMixin,
    BookingUpdatesMixin,
    BookingPaymentsMixin,
    NotificationOutboxMixin,
    NoShowWarningsMixin,
    BookingActionRequestsMixin,
    ClosuresMixin,
    NotificationsDevicesMixin,
    AdminSalonsMixin,
    AdminSalonErasureMixin,
    CategoriesMixin,
    WalkinMixin,
):
    """Database adapter for customer and salon-owner use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
