from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_customer
from app.db.session import get_db
from app.models import Profile
from app.schemas.auth import ProfileOut, ProfileUpdate

router = APIRouter()


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: Profile = Depends(require_customer)) -> Profile:
    return user


@router.patch("/profile", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate,
    user: Profile = Depends(require_customer),
    db: Session = Depends(get_db),
) -> Profile:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

