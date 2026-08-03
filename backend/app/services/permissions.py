from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Profile, Salon, UserRole


def is_super_admin(user: Profile) -> bool:
    return user.role == UserRole.super_admin


def owns_salon(db: Session, user: Profile, salon_id: str) -> bool:
    if is_super_admin(user):
        return True
    return db.scalar(select(Salon.id).where(Salon.id == salon_id, Salon.owner_id == user.id)) is not None


def require_salon_owner(db: Session, user: Profile, salon_id: str) -> None:
    if not owns_salon(db, user, salon_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Salon owner access required")

