from fastapi import APIRouter

from app.api.routes import auth, barber, bookings, customer, notifications, salons

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(customer.router, prefix="/customer", tags=["customer"])
api_router.include_router(salons.router, prefix="/salons", tags=["salons"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(barber.router, prefix="/barber", tags=["barber"])

