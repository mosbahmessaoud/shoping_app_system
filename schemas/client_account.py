from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ClientAccountBase(BaseModel):
    total_amount: Decimal = Field(default=0.00, ge=0, description="Total amount of all bills")
    total_paid: Decimal = Field(default=0.00, ge=0, description="Total amount paid")
    total_remaining: Decimal = Field(default=0.00, ge=0, description="Remaining amount to be paid")
    total_credit: Decimal = Field(default=0.00, ge=0, description="Total credit accumulated")


class ClientAccountCreate(ClientAccountBase):
    client_id: int = Field(..., description="ID of the client")


class ClientAccountUpdate(BaseModel):
    total_amount: Optional[Decimal] = Field(None, ge=0)
    total_paid: Optional[Decimal] = Field(None, ge=0)
    total_remaining: Optional[Decimal] = Field(None, ge=0)
    total_credit: Optional[Decimal] = Field(None, ge=0)


class ClientAccountResponse(ClientAccountBase):
    id: int
    client_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClientAccountWithClient(ClientAccountResponse):
    client_username: Optional[str] = None
    client_email: Optional[str] = None
    client_phone_number: Optional[str] = None
    client_village: Optional[str] = None

    class Config:
        from_attributes = True

