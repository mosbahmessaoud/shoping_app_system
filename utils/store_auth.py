# utils/store_auth.py
#
# JWT authentication helpers for the website/ecommerce dashboard.
# Completely separate from utils/auth.py (which serves the B2B admin).
# Uses the same direct bcrypt pattern as utils/auth.py (bcrypt 5.0.0 compatible).
#
import os
import bcrypt
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models.store_user import StoreUser, StoreUserRole
from utils.db import get_db

# ── Config ────────────────────────────────────────────────────────────────────
STORE_SECRET_KEY = os.getenv("STORE_SECRET_KEY", "change-me-store-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("STORE_TOKEN_EXPIRE_MINUTES", "1440")
)  # 24h

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/store/auth/login")


# ── Password helpers (same pattern as utils/auth.py) ─────────────────────────


def hash_password(plain: str) -> str:
    """
    Hash a password with bcrypt (bcrypt 5.0.0 compatible).
    Passwords longer than 72 bytes are pre-hashed with SHA256 first.
    """
    if len(plain.encode("utf-8")) > 72:
        plain = hashlib.sha256(plain.encode("utf-8")).hexdigest()

    password_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password. Applies the same SHA256 pre-hash if needed.
    """
    if len(plain.encode("utf-8")) > 72:
        plain = hashlib.sha256(plain.encode("utf-8")).hexdigest()

    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Token helpers ─────────────────────────────────────────────────────────────


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, STORE_SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, STORE_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependencies ──────────────────────────────────────────────────────


def get_current_store_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> StoreUser:
    """Any authenticated website-dashboard user (admin OR livreur)."""
    payload = _decode_token(token)
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide"
        )

    user = (
        db.query(StoreUser)
        .filter(
            StoreUser.id == int(user_id),
            StoreUser.is_active == True,
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou désactivé",
        )
    return user


def get_current_store_admin(
    current_user: StoreUser = Depends(get_current_store_user),
) -> StoreUser:
    """Only website-dashboard admins."""
    if current_user.role != StoreUserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs du site",
        )
    return current_user


def get_current_livreur(
    current_user: StoreUser = Depends(get_current_store_user),
) -> StoreUser:
    """Only livreurs."""
    if current_user.role != StoreUserRole.livreur:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux livreurs",
        )
    return current_user
