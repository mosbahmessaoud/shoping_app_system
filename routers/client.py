# routes/client.py (Updated version)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from models.client import Client
from models.bill import Bill
from models.otp import OTP
from schemas.client import ClientCreate, ClientUpdate, ClientLogin, ClientResponse, ClientWithToken, ClientSummary
from utils.db import get_db
from utils.auth import hash_password, verify_password, create_access_token, get_current_client, get_current_admin

router = APIRouter(prefix="/client", tags=["Client"])


@router.post("/register", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def register_client(client_data: ClientCreate, db: Session = Depends(get_db)):
    """Enregistrer un nouveau client (nécessite vérification OTP préalable)"""

    # Vérifier si l'OTP a été vérifié pour cet email
    verified_otp = db.query(OTP).filter(
        OTP.email == client_data.email,
        OTP.otp_type == "registration",
        OTP.is_verified == True,
        OTP.is_used == True
    ).first()

    if not verified_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veuillez d'abord vérifier votre email avec le code OTP"
        )

    # Vérifier si l'email existe déjà
    existing_client = db.query(Client).filter(
        Client.email == client_data.email).first()
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )

    # Vérifier si le nom d'utilisateur existe déjà
    existing_username = db.query(Client).filter(
        Client.username == client_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà utilisé"
        )

    # Vérifier le numéro de téléphone
    existing_phone = db.query(Client).filter(
        Client.phone_number == client_data.phone_number
    ).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce numéro de téléphone est déjà utilisé"
        )

    # Créer le nouveau client
    new_client = Client(
        username=client_data.username,
        email=client_data.email,
        password_hash=hash_password(client_data.password),
        phone_number=client_data.phone_number,
        address=client_data.address,
        city=client_data.city,
        is_active=True  # Account is active after email verification
    )

    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    return new_client


@router.post("/login", response_model=ClientWithToken)
def login_client(login_data: ClientLogin, db: Session = Depends(get_db)):
    """Connexion client"""

    client = db.query(Client).filter(Client.email == login_data.email).first()

    if not client or not verify_password(login_data.password, client.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte est désactivé"
        )

    access_token = create_access_token(
        data={"sub": str(client.id), "type": "client"})

    return {
        "client": client,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=ClientResponse)
def get_current_client_info(current_client: Client = Depends(get_current_client)):
    """Obtenir les informations du client connecté"""
    return current_client


@router.put("/me", response_model=ClientResponse)
def update_client_profile(
    client_data: ClientUpdate,
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """Mettre à jour le profil du client"""

    # Vérifier si le nouvel email existe déjà
    if client_data.email and client_data.email != current_client.email:
        existing = db.query(Client).filter(
            Client.email == client_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )
        current_client.email = client_data.email

    # Vérifier si le nouveau nom d'utilisateur existe déjà
    if client_data.username and client_data.username != current_client.username:
        existing = db.query(Client).filter(
            Client.username == client_data.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà utilisé"
            )
        current_client.username = client_data.username

    # Mettre à jour les autres champs
    if client_data.phone_number is not None:
        current_client.phone_number = client_data.phone_number
    if client_data.address is not None:
        current_client.address = client_data.address
    if client_data.city is not None:
        current_client.city = client_data.city
    if client_data.password:
        current_client.password_hash = hash_password(client_data.password)

    db.commit()
    db.refresh(current_client)

    return current_client


@router.get("/", response_model=List[ClientSummary])
def get_all_clients(
    skip: int = 0,
    limit: int = 100,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir la liste de tous les clients (admin seulement)"""

    clients = db.query(
        Client,
        func.count(Bill.id).label('total_bills'),
        func.coalesce(func.sum(Bill.total_remaining), 0).label('total_debt')
    ).outerjoin(Bill).group_by(Client.id).offset(skip).limit(limit).all()

    result = []
    for client, total_bills, total_debt in clients:
        result.append(ClientSummary(
            id=client.id,
            username=client.username,
            email=client.email,
            phone_number=client.phone_number,
            city=client.city,
            total_bills=total_bills,
            total_debt=float(total_debt),
            is_active=client.is_active
        ))

    return result


@router.get("/{client_id}", response_model=ClientResponse)
def get_client_by_id(
    client_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir un client par son ID (admin seulement)"""

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )

    return client


@router.patch("/{client_id}/toggle-active", response_model=ClientResponse)
def toggle_client_active(
    client_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Activer/désactiver un client (admin seulement)"""

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )

    client.is_active = not client.is_active
    db.commit()
    db.refresh(client)

    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Supprimer un client (admin seulement)"""

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )

    db.delete(client)
    db.commit()

    return None
