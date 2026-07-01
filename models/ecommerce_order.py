# models/ecommerce_order.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from utils.db import Base


class CallingStatus(str, enum.Enum):
    not_called = "not_called"
    call1 = "call1"
    call2 = "call2"
    call3 = "call3"
    no_answer = "no_answer"
    unreachable = "unreachable"
    confirmed_by_phone = "confirmed_by_phone"
    cancelled_by_phone = "cancelled_by_phone"


class DeliveryStatus(str, enum.Enum):
    not_shipped = "not_shipped"
    shipped = "shipped"
    delivered = "delivered"
    returned = "returned"
    cancelled = "cancelled"  # ← replaces OrderStatus.cancelled


class EcommerceOrder(Base):
    __tablename__ = "ecommerce_orders"

    id = Column(Integer, primary_key=True, index=True)

    # ── Customer / lead info ──────────────────────────────────────────────────
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)

    # ── Shipping location ─────────────────────────────────────────────────────
    wilaya_id = Column(Integer, nullable=False)
    wilaya_name = Column(String(100), nullable=False)
    baladia_id = Column(Integer, nullable=False)
    baladia_name = Column(String(100), nullable=False)
    address_details = Column(String(500), nullable=True)

    # ── Ordered product ───────────────────────────────────────────────────────
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    product_name_snapshot = Column(String(300), nullable=False)
    unit_price_snapshot = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    selected_variants = Column(Text, nullable=True)  # JSON string
    total_price = Column(Numeric(10, 2), nullable=False)

    # ── Tracking ──────────────────────────────────────────────────────────────
    tracking_code = Column(String(20), nullable=True, unique=True, index=True)

    # ── Status axes ───────────────────────────────────────────────────────────
    # delivery_status is now the single lifecycle axis (livreur owns it A→Z).
    # Values: not_shipped → shipped → delivered → returned | cancelled
    delivery_status = Column(
        SAEnum(DeliveryStatus, name="delivery_status"),
        nullable=False,
        default=DeliveryStatus.not_shipped,
        index=True,
    )
    calling_status = Column(
        SAEnum(CallingStatus, name="calling_status"),
        nullable=False,
        default=CallingStatus.not_called,
        index=True,
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = Column(String(1000), nullable=True)
    livreur_notes = Column(String(1000), nullable=True)

    # ── Assignment & visibility ───────────────────────────────────────────────
    assigned_livreur_id = Column(
        Integer,
        ForeignKey("store_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_hidden_from_livreurs = Column(Boolean, nullable=False, default=False)

    # ── Notification tracking ─────────────────────────────────────────────────
    telegram_notified = Column(Boolean, nullable=False, default=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    product = relationship("Product", lazy="joined")
    assigned_livreur = relationship(
        "StoreUser",
        foreign_keys=[assigned_livreur_id],
        back_populates="assigned_orders",
    )
