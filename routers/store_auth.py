# routers/store_auth.py
#
# Authentication + user management for the website/ecommerce dashboard.
# Routes are mounted under /store/auth  and  /store/users
#
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models.store_user import StoreUser, StoreUserRole
from schemas.store_user import (
    StoreUserLogin,
    StoreTokenResponse,
    StoreUserCreate,
    StoreUserUpdate,
    StoreUserResponse,
)
from utils.db import get_db
from utils.store_auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_store_user,
    get_current_store_admin,
)

router = APIRouter(prefix="/store", tags=["Store Dashboard - Auth"])


# ── Login ─────────────────────────────────────────────────────────────────────


@router.post("/auth/login", response_model=StoreTokenResponse)
def store_login(credentials: StoreUserLogin, db: Session = Depends(get_db)):
    """
    Login for website dashboard users (admin + livreur).
    Returns a JWT valid for 24 h by default (STORE_TOKEN_EXPIRE_MINUTES env var).
    """
    user = db.query(StoreUser).filter(StoreUser.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé. Contactez l'administrateur.",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role.value})

    return StoreTokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
    )


# ── Current user (self) ───────────────────────────────────────────────────────


@router.get("/auth/me", response_model=StoreUserResponse)
def get_me(current_user: StoreUser = Depends(get_current_store_user)):
    """Return the currently authenticated user's profile."""
    return current_user


# ── User management (admin only) ──────────────────────────────────────────────


@router.get(
    "/users",
    response_model=List[StoreUserResponse],
    tags=["Store Dashboard - Users (Admin)"],
)
def list_store_users(
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    """List all dashboard users (admins + livreurs)."""
    return db.query(StoreUser).order_by(StoreUser.created_at.desc()).all()


@router.post(
    "/users",
    response_model=StoreUserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Store Dashboard - Users (Admin)"],
)
def create_store_user(
    user_data: StoreUserCreate,
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    """Create a new dashboard user (admin or livreur). Admin only."""
    existing = db.query(StoreUser).filter(StoreUser.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà",
        )

    new_user = StoreUser(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        phone_number=user_data.phone_number,
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get(
    "/users/{user_id}",
    response_model=StoreUserResponse,
    tags=["Store Dashboard - Users (Admin)"],
)
def get_store_user(
    user_id: int,
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    """Get a specific dashboard user by ID. Admin only."""
    user = db.query(StoreUser).filter(StoreUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable",
        )
    return user


@router.patch(
    "/users/{user_id}",
    response_model=StoreUserResponse,
    tags=["Store Dashboard - Users (Admin)"],
)
def update_store_user(
    user_id: int,
    update_data: StoreUserUpdate,
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    """Update a dashboard user (name, phone, role, active, password). Admin only."""
    user = db.query(StoreUser).filter(StoreUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable",
        )

    if update_data.full_name is not None:
        user.full_name = update_data.full_name
    if update_data.phone_number is not None:
        user.phone_number = update_data.phone_number
    if update_data.is_active is not None:
        user.is_active = update_data.is_active
    if update_data.role is not None:
        user.role = update_data.role
    if update_data.password is not None:
        user.password_hash = hash_password(update_data.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Store Dashboard - Users (Admin)"],
)
def delete_store_user(
    user_id: int,
    current_admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    """Delete a dashboard user. Admin only. Cannot delete yourself."""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas supprimer votre propre compte",
        )

    user = db.query(StoreUser).filter(StoreUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable",
        )

    db.delete(user)
    db.commit()
    return None


@router.post("/auth/init-admin", include_in_schema=False)
def init_first_admin(db: Session = Depends(get_db)):
    # Block if any admin already exists
    existing = db.query(StoreUser).filter(StoreUser.role == StoreUserRole.admin).first()
    if existing:
        raise HTTPException(status_code=400, detail="Un admin existe déjà")

    admin = StoreUser(
        full_name="Admin Principal",
        email="toufikbisnese@gmail.com",
        password_hash=hash_password("mosbah12"),
        role=StoreUserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin créé", "email": admin.email}
