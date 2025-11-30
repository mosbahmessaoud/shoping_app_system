import os
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models.admin import Admin
from models.client import Client
from utils.db import get_db
import hashlib

# Configuration de sécurité
# Changez ceci en production!
SECRET_KEY = os.getenv(
    "SECRET_KEY", "votre_clé_secrète_très_sécurisée_changez_moii_enn_productionn")
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 20  # 24 heures

# OAuth2 scheme pour l'extraction du token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str) -> str:
    """
    Hacher un mot de passe avec bcrypt.
    Bcrypt a une limite de 72 octets, donc on pré-hache les mots de passe longs avec SHA256.
    """
    # Si le mot de passe dépasse 72 octets, on le pré-hache avec SHA256
    if len(password.encode('utf-8')) > 72:
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    # Hacher avec bcrypt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifier un mot de passe.
    Applique le même pré-hachage si nécessaire.
    """
    # Appliquer le même pré-hachage si le mot de passe est long
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = hashlib.sha256(
            plain_password.encode('utf-8')).hexdigest()

    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')

    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Créer un token JWT"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obtenir l'utilisateur actuel (admin ou client) à partir du token"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_type: str = payload.get("type")

        if user_id is None or user_type is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Récupérer l'utilisateur en fonction du type
    if user_type == "admin":
        user = db.query(Admin).filter(Admin.id == int(user_id)).first()
    elif user_type == "client":
        user = db.query(Client).filter(Client.id == int(user_id)).first()
    else:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    return {"user": user, "type": user_type}


def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Admin:
    """Obtenir l'admin actuel (uniquement pour les routes admin)"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )

    forbidden_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès refusé. Droits administrateur requis"
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_type: str = payload.get("type")

        if user_id is None or user_type is None:
            raise credentials_exception

        if user_type != "admin":
            raise forbidden_exception

    except JWTError:
        raise credentials_exception

    admin = db.query(Admin).filter(Admin.id == int(user_id)).first()

    if admin is None:
        raise credentials_exception

    return admin


def get_current_client(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Client:
    """Obtenir le client actuel (uniquement pour les routes client)"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )

    forbidden_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès refusé. Vous devez être connecté en tant que client"
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_type: str = payload.get("type")

        if user_id is None or user_type is None:
            raise credentials_exception

        if user_type != "client":
            raise forbidden_exception

    except JWTError:
        raise credentials_exception

    client = db.query(Client).filter(Client.id == int(user_id)).first()

    if client is None:
        raise credentials_exception

    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte est désactivé"
        )

    return client
