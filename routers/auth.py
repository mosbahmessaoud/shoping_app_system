from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.client import Client
from models.admin import Admin
from schemas.auth import UserTypeRequest, UserTypeResponse
from utils.db import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


# geting the type of user "admin or client "by his email
@router.post("/type_user", response_model=UserTypeResponse)
def get_user_type(request: UserTypeRequest, db: Session = Depends(get_db)):
    """detict user type """

    # Check if email exists in Client table
    client = db.query(Client).filter(Client.email == request.email).first()
    if client:
        return UserTypeResponse(user_type="client", exists=True)

    # Check if email exists in Admin table
    admin = db.query(Admin).filter(Admin.email == request.email).first()
    if admin:
        return UserTypeResponse(user_type="admin", exists=True)

    # Email doesnt exist raise 404 error
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Aucun compte n'existe avec cet email"
    )
