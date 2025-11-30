from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Admin Base Schema
class AdminBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=20)

# Admin Create Schema (for registration)
class AdminCreate(AdminBase):
    password: str = Field(..., min_length=8)

# Admin Update Schema
class AdminUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    password: Optional[str] = Field(None, min_length=8)

# Admin Login Schema
class AdminLogin(BaseModel):
    email: EmailStr
    password: str

# Admin Response Schema
class AdminResponse(AdminBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Admin with Token (after login)
class AdminWithToken(BaseModel):
    admin: AdminResponse
    access_token: str
    token_type: str = "bearer"