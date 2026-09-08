"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.routes import (
    admin,
    auth,
    bookings,
    customer,
    notifications,
    owner,
    profiles,
    walkin,
)

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(customer.router, prefix="/customer", tags=["customer"])
api_v1_router.include_router(owner.router, prefix="/salons", tags=["salon owner"])
api_v1_router.include_router(customer.salons_router, tags=["salons"])
api_v1_router.include_router(customer.catalog_router, prefix="/catalog", tags=["catalog"])
api_v1_router.include_router(bookings.router, tags=["bookings"])
api_v1_router.include_router(notifications.router, tags=["notifications"])
api_v1_router.include_router(walkin.router, prefix="/walkin", tags=["walkin"])
