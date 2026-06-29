# models/ecommerce_order.py  (UPDATED — added tracking_code column)
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

# ── Enums ────────────────────────────────────────────────────────────────────


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


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


# ── Model ────────────────────────────────────────────────────────────────────


class EcommerceOrder(Base):
    __tablename__ = "ecommerce_orders"

    id = Column(Integer, primary_key=True, index=True)

    # ── Customer / lead info ─────────────────────────────────────────────────
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
    # Short human-readable code  e.g.  AB-4829-KT
    # Unique per order — customers use it to track delivery status.
    # nullable=True so existing rows without a code don't break.
    tracking_code = Column(String(20), nullable=True, unique=True, index=True)

    # ── Status axes ───────────────────────────────────────────────────────────
    status = Column(
        SAEnum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.pending,
        index=True,
    )
    calling_status = Column(
        SAEnum(CallingStatus, name="calling_status"),
        nullable=False,
        default=CallingStatus.not_called,
        index=True,
    )
    delivery_status = Column(
        SAEnum(DeliveryStatus, name="delivery_status"),
        nullable=False,
        default=DeliveryStatus.not_shipped,
        index=True,
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = Column(String(1000), nullable=True)  # admin notes
    livreur_notes = Column(String(1000), nullable=True)  # livreur field notes

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


# # models/ecommerce_order.py
# from sqlalchemy import (
#     Column,
#     Integer,
#     String,
#     Numeric,
#     DateTime,
#     ForeignKey,
#     Text,
#     Boolean,
# )
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func
# from utils.db import Base


# class EcommerceOrder(Base):
#     """
#     COD (Cash on Delivery) order placed by an individual customer
#     through the public storefront. Fully separate from Client/Bill
#     (which serve the B2B professional side). No authentication
#     is involved in creating these rows.
#     """

#     __tablename__ = "ecommerce_orders"

#     id = Column(Integer, primary_key=True, index=True)

#     # Lead / customer info (no account required)
#     full_name = Column(String(150), nullable=False)
#     phone_number = Column(String(20), nullable=False, index=True)

#     # Shipping location (Algeria wilaya/baladia system)
#     wilaya_id = Column(Integer, nullable=False)
#     wilaya_name = Column(String(100), nullable=False)
#     baladia_id = Column(Integer, nullable=False)
#     baladia_name = Column(String(100), nullable=False)
#     address_details = Column(String(500), nullable=True)

#     # Ordered product (single product per order row; quantity covers multiples)
#     product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
#     product_name_snapshot = Column(String(300), nullable=False)
#     unit_price_snapshot = Column(Numeric(10, 2), nullable=False)
#     quantity = Column(Integer, nullable=False, default=1)
#     selected_variants = Column(
#         Text, nullable=True
#     )  # JSON string, e.g. {"size": "M", "color": "Red"}
#     total_price = Column(Numeric(10, 2), nullable=False)

#     # Order lifecycle - simple COD pipeline
#     # pending -> confirmed -> shipped -> delivered  (or cancelled at any point)
#     status = Column(String(30), nullable=False, default="pending", index=True)
#     notes = Column(String(500), nullable=True)

#     # Notification tracking
#     telegram_notified = Column(Boolean, nullable=False, default=False)

#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

#     product = relationship("Product", lazy="joined")
