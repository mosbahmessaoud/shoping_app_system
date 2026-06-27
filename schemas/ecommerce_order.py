# schemas/ecommerce_order.py  (UPDATED)
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from models.ecommerce_order import OrderStatus, CallingStatus, DeliveryStatus

# ── Public storefront (customer-facing, unchanged) ────────────────────────────


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


# ── Dashboard: admin update ───────────────────────────────────────────────────


class EcommerceOrderAdminUpdate(BaseModel):
    """
    Fields that a store ADMIN can update.
    All fields optional — send only what you want to change (PATCH semantics).
    """

    status: Optional[OrderStatus] = None
    calling_status: Optional[CallingStatus] = None
    delivery_status: Optional[DeliveryStatus] = None
    notes: Optional[str] = None  # admin notes
    assigned_livreur_id: Optional[int] = None  # None = unassign
    is_hidden_from_livreurs: Optional[bool] = None


# ── Dashboard: livreur update ─────────────────────────────────────────────────


class EcommerceOrderLivreurUpdate(BaseModel):
    """
    Fields that a LIVREUR can update on orders assigned/visible to them.
    Livreur cannot touch: status, notes, assignment, visibility.
    """

    calling_status: Optional[CallingStatus] = None
    delivery_status: Optional[DeliveryStatus] = None
    livreur_notes: Optional[str] = None


# ── Responses ─────────────────────────────────────────────────────────────────


class EcommerceOrderResponse(BaseModel):
    id: int

    # Customer
    full_name: str
    phone_number: str

    # Location
    wilaya_id: int
    wilaya_name: str
    baladia_id: int
    baladia_name: str
    address_details: Optional[str]

    # Product
    product_id: int
    product_name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    selected_variants: Optional[str]  # raw JSON string
    total_price: Decimal

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

    # Notifications
    telegram_notified: bool

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EcommerceOrderSummary(BaseModel):
    """Aggregate counts per status — used by the dashboard home cards."""

    # By main status
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int

    # By calling status
    not_called_orders: int
    confirmed_by_phone_orders: int
    cancelled_by_phone_orders: int
    unreachable_orders: int

    # By delivery status
    not_shipped_orders: int
    in_delivery_orders: int  # shipped (physical)
    delivered_orders_delivery: int
    returned_orders: int


# ── Legacy schema kept for backward compat with existing public_order.py ──────


class EcommerceOrderUpdate(BaseModel):
    """
    Kept for backward compatibility with the existing public /admin/orders PATCH.
    New dashboard code should use EcommerceOrderAdminUpdate instead.
    """

    status: Optional[str] = None
    notes: Optional[str] = None
