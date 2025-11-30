from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Client Base Schema


class ClientBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)

# Client Create Schema (for registration)


class ClientCreate(ClientBase):
    password: str = Field(..., min_length=8)

# Client Update Schema


class ClientUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None

# Client Login Schema


class ClientLogin(BaseModel):
    email: EmailStr
    password: str

# Client Response Schema


class ClientResponse(ClientBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Client with Token (after login)


class ClientWithToken(BaseModel):
    client: ClientResponse
    access_token: str
    token_type: str = "bearer"

# Client Summary (for admin view)


class ClientSummary(BaseModel):
    id: int
    username: str
    email: EmailStr
    phone_number: Optional[str]
    city: Optional[str]
    total_bills: int = 0
    total_debt: float = 0.0
    is_active: bool

    class Config:
        from_attributes = True
