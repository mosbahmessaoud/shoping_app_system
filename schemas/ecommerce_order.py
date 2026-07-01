# schemas/ecommerce_order.py
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from models.ecommerce_order import CallingStatus, DeliveryStatus

# ── Public storefront — order creation ───────────────────────────────────────


class EcommerceOrderCreate(BaseModel):
    full_name: str
    phone_number: str
    wilaya_id: int
    baladia_id: int
    address_details: Optional[str] = None
    product_id: int
    quantity: int = 1
    selected_variants: Optional[Dict[str, Any]] = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("La quantité doit être au moins 1")
        return v


class EcommerceOrderCreatedResponse(BaseModel):
    message: str
    order_id: int
    total_price: Decimal
    tracking_code: str
    qr_code_base64: str
    tracking_url: str


# ── Public tracking (no auth) ─────────────────────────────────────────────────


class OrderTrackingResponse(BaseModel):
    tracking_code: str
    order_id: int
    product_name: str
    wilaya_name: str
    baladia_name: str
    quantity: int
    delivery_status: DeliveryStatus
    created_at: datetime
    updated_at: Optional[datetime]


# ── Dashboard: admin update ───────────────────────────────────────────────────


class EcommerceOrderAdminUpdate(BaseModel):
    delivery_status: Optional[DeliveryStatus] = None
    calling_status: Optional[CallingStatus] = None
    notes: Optional[str] = None
    assigned_livreur_id: Optional[int] = None
    is_hidden_from_livreurs: Optional[bool] = None


# ── Dashboard: livreur update ─────────────────────────────────────────────────


class EcommerceOrderLivreurUpdate(BaseModel):
    calling_status: Optional[CallingStatus] = None
    delivery_status: Optional[DeliveryStatus] = None
    livreur_notes: Optional[str] = None


# ── Full order response (dashboard) ──────────────────────────────────────────


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
    tracking_code: Optional[str]
    delivery_status: DeliveryStatus
    calling_status: CallingStatus
    notes: Optional[str]
    livreur_notes: Optional[str]
    assigned_livreur_id: Optional[int]
    is_hidden_from_livreurs: bool
    telegram_notified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Summary ───────────────────────────────────────────────────────────────────


class EcommerceOrderSummary(BaseModel):
    total_orders: int
    # Delivery axis
    not_shipped_orders: int
    in_delivery_orders: int
    delivered_orders: int
    returned_orders: int
    cancelled_orders: int
    # Calling axis
    not_called_orders: int
    confirmed_by_phone_orders: int
    cancelled_by_phone_orders: int
    unreachable_orders: int
