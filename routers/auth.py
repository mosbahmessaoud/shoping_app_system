from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.client import Client
from models.admin import Admin
from utils.db import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


class UserTypeRequest(BaseModel):
    email: str


class UserTypeResponse(BaseModel):
    user_type: str
    exists: bool


@router.post("/type_user", response_model=UserTypeResponse)
def get_user_type(request: UserTypeRequest, db: Session = Depends(get_db)):
    """Determine if email exists and what type of user it is"""

    # Check if email exists in Client table
    client = db.query(Client).filter(Client.email == request.email).first()
    if client:
        return UserTypeResponse(user_type="client", exists=True)

    # Check if email exists in Admin table
    admin = db.query(Admin).filter(Admin.email == request.email).first()
    if admin:
        return UserTypeResponse(user_type="admin", exists=True)

    # Email doesn't exist - raise 404 error
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Aucun compte n'existe avec cet email"
    )
