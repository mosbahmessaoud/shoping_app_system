from pydoc import cli
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from models.admin import Admin
from schemas.admin import AdminCreate, AdminUpdate, AdminLogin, AdminResponse, AdminWithToken
from models.client import Client
from utils.db import get_db
from utils.auth import hash_password, verify_password, create_access_token, get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])



@router.post("/register", response_model=AdminWithToken, status_code=status.HTTP_201_CREATED)
def register_admin(admin_data: AdminCreate, db: Session = Depends(get_db)):
    """Inscription d'un nouvel administrateur"""
    
    # Vérifier si l'email existe déjà
    existing_admin = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )
    
    # Vérifier si le nom d'utilisateur existe déjà
    existing_username = db.query(Admin).filter(Admin.username == admin_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà utilisé"
        )
    
    # Créer le nouvel administrateur
    new_admin = Admin(
        username=admin_data.username,
        email=admin_data.email,
        password_hash=hash_password(admin_data.password),
        phone_number=admin_data.phone_number
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    # Créer un token d'accès pour l'administrateur nouvellement enregistré
    access_token = create_access_token(
        data={"sub": str(new_admin.id), "type": "admin"}
    )
    
    return {
        "admin": new_admin,
        "access_token": access_token,
        "token_type": "bearer"
    }



@router.post("/login", response_model=AdminWithToken)
def login_admin(login_data: AdminLogin, db: Session = Depends(get_db)):
    """Connexion administrateur"""

    admin = db.query(Admin).filter(Admin.email == login_data.email).first()

    if not admin or not verify_password(login_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    access_token = create_access_token(
        data={"sub": str(admin.id), "type": "admin"})

    return {
        "admin": admin,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=AdminResponse, dependencies=[Depends(get_current_admin)])
def get_current_admin_info(current_admin: Admin = Depends(get_current_admin)):
    """Obtenir les informations de l'administrateur connecté"""
    return current_admin


@router.put("/me", response_model=AdminResponse, dependencies=[Depends(get_current_admin)])
def update_admin_profile(
    admin_data: AdminUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil de l'administrateur"""

    # Vérifier si le nouvel email existe déjà
    if admin_data.email and admin_data.email != current_admin.email:
        existing = db.query(Admin).filter(
            Admin.email == admin_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )
        current_admin.email = admin_data.email

    # Vérifier si le nouveau nom d'utilisateur existe déjà
    if admin_data.username and admin_data.username != current_admin.username:
        existing = db.query(Admin).filter(
            Admin.username == admin_data.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà utilisé"
            )
        current_admin.username = admin_data.username

    # Mettre à jour les autres champs
    if admin_data.phone_number is not None:
        current_admin.phone_number = admin_data.phone_number

    if admin_data.password:
        current_admin.password_hash = hash_password(admin_data.password)

    db.commit()
    db.refresh(current_admin)

    return current_admin


@router.get("/", response_model=List[AdminResponse], dependencies=[Depends(get_current_admin)])
def get_all_admins(
    skip: int = 0,
    limit: int = 100,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir la liste de tous les administrateurs"""
    admins = db.query(Admin).offset(skip).limit(limit).all()
    return admins


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
def delete_admin(
    admin_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Supprimer un administrateur"""

    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas supprimer votre propre compte"
        )

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrateur non trouvé"
        )

    db.delete(admin)
    db.commit()

    return None


@router.post("/type_of_user", response_model=str)
def get_type_of_user(login_data: AdminLogin, db: Session = Depends(get_db)):
    """Vérifier le type d'utilisateur"""

    admin = db.query(Admin).filter(Admin.email == login_data.email).first()
    client = db.query(Client).filter(Client.email == login_data.email).first()

    if admin:
        return "admin"
    elif client:
        return "client"
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
