# schemas/ecommerce_order.py  (UPDATED — tracking_code + qr_code_base64 in response)
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from models.ecommerce_order import OrderStatus, CallingStatus, DeliveryStatus

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
    """
    Returned immediately after a successful order submission.
    Includes the tracking code + QR code so the customer can
    save/download them right away.
    """

    message: str
    order_id: int
    total_price: Decimal

    # Tracking assets — display these to the customer on the confirmation page
    tracking_code: str  # e.g. "AB-4829-KT"
    qr_code_base64: (
        str  # PNG encoded as base64 — use as <img src="data:image/png;base64,{...}">
    )
    tracking_url: str  # Full URL the QR code encodes


# ── Public tracking (no auth) ─────────────────────────────────────────────────


class OrderTrackingResponse(BaseModel):
    """
    What the customer sees when they track their order.
    Intentionally minimal — no personal or pricing data exposed.
    """

    tracking_code: str
    order_id: int
    product_name: str
    wilaya_name: str
    baladia_name: str
    quantity: int

    # The three status axes, customer-friendly
    status: OrderStatus
    delivery_status: DeliveryStatus

    created_at: datetime
    updated_at: Optional[datetime]


# ── Dashboard: admin update ───────────────────────────────────────────────────


class EcommerceOrderAdminUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    calling_status: Optional[CallingStatus] = None
    delivery_status: Optional[DeliveryStatus] = None
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

    # Tracking
    tracking_code: Optional[str]  # nullable for old orders that predate this feature

    # Status axes
    status: OrderStatus
    calling_status: CallingStatus
    delivery_status: DeliveryStatus

    # Notes
    notes: Optional[str]
    livreur_notes: Optional[str]

    # Assignment & visibility
    assigned_livreur_id: Optional[int]
    is_hidden_from_livreurs: bool

    telegram_notified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Summary ───────────────────────────────────────────────────────────────────


class EcommerceOrderSummary(BaseModel):
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    not_called_orders: int
    confirmed_by_phone_orders: int
    cancelled_by_phone_orders: int
    unreachable_orders: int
    not_shipped_orders: int
    in_delivery_orders: int
    delivered_orders_delivery: int
    returned_orders: int


# ── Legacy ────────────────────────────────────────────────────────────────────


class EcommerceOrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
