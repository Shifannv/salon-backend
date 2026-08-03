from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models import Profile, UserRole
from app.schemas.auth import LoginRequest, ProfileOut, Token, UserCreate

router = APIRouter()


@router.post("/register", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> Profile:
    if payload.role in {UserRole.super_admin, UserRole.staff}:
        raise HTTPException(status_code=400, detail="This role cannot self-register")
    if db.scalar(select(Profile.id).where(Profile.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = Profile(
        full_name=payload.full_name,
        email=str(payload.email),
        phone=payload.phone,
        role=payload.role,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(Profile).where(Profile.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return Token(access_token=token)


@router.get("/me", response_model=ProfileOut)
def me(user: Profile = Depends(get_current_user)) -> Profile:
    return user

