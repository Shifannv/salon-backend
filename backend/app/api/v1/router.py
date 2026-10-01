"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.routes import (
    admin,
    auth,
    booking_actions,
    bookings,
    customer,
    media,
    notifications,
    owner,
    profiles,
    reports,
    walkin,
)

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(media.router, tags=["media"])
api_v1_router.include_router(reports.router, tags=["reports"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(customer.router, prefix="/customer", tags=["customer"])
api_v1_router.include_router(owner.router, prefix="/salons", tags=["salon owner"])
api_v1_router.include_router(customer.salons_router, tags=["salons"])
api_v1_router.include_router(customer.catalog_router, prefix="/catalog", tags=["catalog"])
api_v1_router.include_router(bookings.router, tags=["bookings"])
api_v1_router.include_router(booking_actions.router, tags=["booking actions"])
api_v1_router.include_router(notifications.router, tags=["notifications"])
api_v1_router.include_router(walkin.router, prefix="/walkin", tags=["walkin"])
