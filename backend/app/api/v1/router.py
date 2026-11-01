"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.routes import (
    account_deletion,
    admin,
    admin_insights,
    auth,
    booking_actions,
    booking_finance,
    bookings,
    customer,
    finance,
    media,
    notifications,
    owner,
    payments,
    profiles,
    reports,
    subscription_billing,
    subscriptions,
    support,
    walkin,
    wallet,
)
from app.core.config import settings

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(
    account_deletion.router, prefix="/account/deletion", tags=["account deletion"]
)
api_v1_router.include_router(
    account_deletion.admin_router, prefix="/admin", tags=["account deletion"]
)
api_v1_router.include_router(media.router, tags=["media"])
api_v1_router.include_router(reports.router, tags=["reports"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(customer.router, prefix="/customer", tags=["customer"])
api_v1_router.include_router(owner.router, prefix="/salons", tags=["salon owner"])
api_v1_router.include_router(payments.router, tags=["payments"])
api_v1_router.include_router(finance.router, tags=["owner finance"])
api_v1_router.include_router(wallet.router, tags=["owner wallet"])
api_v1_router.include_router(wallet.admin_router, prefix="/admin", tags=["admin wallet"])
api_v1_router.include_router(support.router, tags=["support"])
api_v1_router.include_router(customer.salons_router, tags=["salons"])
api_v1_router.include_router(customer.catalog_router, prefix="/catalog", tags=["catalog"])
api_v1_router.include_router(bookings.router, tags=["bookings"])
api_v1_router.include_router(booking_finance.router, tags=["booking finance"])
api_v1_router.include_router(booking_actions.router, tags=["booking actions"])
api_v1_router.include_router(notifications.router, tags=["notifications"])
api_v1_router.include_router(walkin.router, prefix="/walkin", tags=["walkin"])
api_v1_router.include_router(subscriptions.router, prefix="/admin", tags=["subscriptions"])
api_v1_router.include_router(admin_insights.router, prefix="/admin", tags=["admin insights"])
api_v1_router.include_router(subscription_billing.router, tags=["subscription billing"])

# The webhook path 404s unless a payment OR subscription webhook provider is configured.
if settings.booking_payments_enabled or settings.subscription_webhook_provider is not None:
    from app.api.v1.routes import webhooks

    api_v1_router.include_router(webhooks.router, tags=["webhooks"])
