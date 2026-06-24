# schemas/ecommerce_order.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict
from decimal import Decimal

# ---------- Create (public, no-auth) ----------


class EcommerceOrderCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    phone_number: str = Field(..., min_length=8, max_length=20)

    wilaya_id: int
    baladia_id: int
    address_details: Optional[str] = Field(None, max_length=500)

    product_id: int
    quantity: int = Field(default=1, ge=1, le=50)
    selected_variants: Optional[Dict[str, str]] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        cleaned = v.strip().replace(" ", "")
        if not cleaned.isdigit() and not cleaned.startswith("+"):
            raise ValueError("Numéro de téléphone invalide")
        digits = cleaned.lstrip("+")
        if not digits.isdigit():
            raise ValueError("Numéro de téléphone invalide")
        if len(digits) < 8 or len(digits) > 15:
            raise ValueError("Numéro de téléphone invalide")
        return cleaned

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Nom complet invalide")
        return v


# ---------- Update (admin only) ----------


class EcommerceOrderUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            allowed = {"pending", "confirmed", "shipped", "delivered", "cancelled"}
            if v not in allowed:
                raise ValueError(
                    f"Statut invalide. Valeurs autorisées: {', '.join(allowed)}"
                )
        return v


# ---------- Response ----------


class EcommerceOrderResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    wilaya_id: int
    wilaya_name: str
    baladia_id: int
    baladia_name: str
    address_details: Optional[str]
    product_id: int
    product_name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    selected_variants: Optional[str]
    total_price: Decimal
    status: str
    notes: Optional[str]
    telegram_notified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class EcommerceOrderSummary(BaseModel):
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int

    class Config:
        from_attributes = True


class EcommerceOrderCreatedResponse(BaseModel):
    """What we hand back to the storefront right after a customer submits an order."""

    message: str
    order_id: int
    total_price: Decimal
