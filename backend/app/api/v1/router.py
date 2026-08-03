"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.routes import auth

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
