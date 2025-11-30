from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

# Bill Item Schema (for creating bill)
class BillItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

# Bill Item Response Schema
class BillItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

# Bill Create Schema
class BillCreate(BaseModel):
    items: List[BillItemCreate] = Field(..., min_length=1)

# Bill Base Schema
class BillBase(BaseModel):
    bill_number: str
    total_amount: Decimal
    total_paid: Decimal
    total_remaining: Decimal
    status: str  # "paid" or "not paid"

# Bill Response Schema
class BillResponse(BillBase):
    id: int
    client_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    notification_sent: bool

    class Config:
        from_attributes = True

# Bill with Items (detailed view)
class BillWithItems(BillResponse):
    items: List[BillItemResponse] = []

    class Config:
        from_attributes = True

# Bill with Client Info (for admin view)
class BillWithClient(BillWithItems):
    client_name: str
    client_email: str
    client_phone: Optional[str]

    class Config:
        from_attributes = True

# Bill Summary
class BillSummary(BaseModel):
    total_bills: int
    total_revenue: Decimal
    total_paid: Decimal
    total_pending: Decimal
    paid_bills: int
    unpaid_bills: int

    class Config:
        from_attributes = True