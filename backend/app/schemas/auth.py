from pydantic import EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import APIModel


class UserCreate(APIModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str | None = None
    role: UserRole = UserRole.customer


class LoginRequest(APIModel):
    email: EmailStr
    password: str


class Token(APIModel):
    access_token: str
    token_type: str = "bearer"


class ProfileOut(APIModel):
    id: str
    role: UserRole
    full_name: str | None
    email: EmailStr
    phone: str | None
    phone_verified: bool
    avatar_url: str | None
    is_active: bool


class ProfileUpdate(APIModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    avatar_url: str | None = None

