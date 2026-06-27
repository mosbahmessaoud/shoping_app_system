# schemas/store_user.py
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from models.store_user import StoreUserRole

# ── Auth ──────────────────────────────────────────────────────────────────────


class StoreUserLogin(BaseModel):
    email: EmailStr
    password: str


class StoreTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    role: StoreUserRole


# ── Create / Update ───────────────────────────────────────────────────────────


class StoreUserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    role: StoreUserRole = StoreUserRole.livreur

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v


class StoreUserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[StoreUserRole] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v


# ── Response ──────────────────────────────────────────────────────────────────


class StoreUserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone_number: Optional[str]
    role: StoreUserRole
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class StoreUserBrief(BaseModel):
    """Minimal livreur info embedded inside order responses."""

    id: int
    full_name: str
    phone_number: Optional[str]

    model_config = {"from_attributes": True}
