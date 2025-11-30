

from http.client import HTTPException
from sys import prefix
from fastapi import APIRouter, Depends, FastAPI, status
from sqlalchemy.orm import Session

from models.admin import Admin
from models.client import Client
from routers.admin import login_admin
from schemas.admin import AdminLogin
from utils.db import get_db
from utils.auth import verify_password


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/type_user", response_model=str)
def get_user_type(data: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == data.email).first()
    client = db.query(Client).filter(Client.email == data.email).first()

    if admin:
        return "admin"
    elif client:
        return "client"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
