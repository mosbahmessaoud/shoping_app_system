from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

# Payment Base Schema
class PaymentBase(BaseModel):
    amount_paid: Decimal = Field(..., gt=0, decimal_places=2)
    payment_method: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)
    payment_date: datetime

# Payment Create Schema
class PaymentCreate(PaymentBase):
    bill_id: int

# Payment Update Schema
class PaymentUpdate(BaseModel):
    amount_paid: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    payment_method: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)
    payment_date: Optional[datetime] = None

# Payment Response Schema
class PaymentResponse(PaymentBase):
    id: int
    bill_id: int
    admin_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Payment with Bill Info
class PaymentWithBillInfo(PaymentResponse):
    bill_number: str
    client_name: str
    bill_total: Decimal
    bill_remaining: Decimal

    class Config:
        from_attributes = True

# Payment History for a Bill
class PaymentHistory(BaseModel):
    bill_id: int
    bill_number: str
    total_amount: Decimal
    total_paid: Decimal
    total_remaining: Decimal
    payments: list[PaymentResponse] = []

    class Config:
        from_attributes = True