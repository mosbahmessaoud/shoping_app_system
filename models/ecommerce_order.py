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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.db import Base


class EcommerceOrder(Base):
    """
    COD (Cash on Delivery) order placed by an individual customer
    through the public storefront. Fully separate from Client/Bill
    (which serve the B2B professional side). No authentication
    is involved in creating these rows.
    """

    __tablename__ = "ecommerce_orders"

    id = Column(Integer, primary_key=True, index=True)

    # Lead / customer info (no account required)
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)

    # Shipping location (Algeria wilaya/baladia system)
    wilaya_id = Column(Integer, nullable=False)
    wilaya_name = Column(String(100), nullable=False)
    baladia_id = Column(Integer, nullable=False)
    baladia_name = Column(String(100), nullable=False)
    address_details = Column(String(500), nullable=True)

    # Ordered product (single product per order row; quantity covers multiples)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    product_name_snapshot = Column(String(300), nullable=False)
    unit_price_snapshot = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    selected_variants = Column(
        Text, nullable=True
    )  # JSON string, e.g. {"size": "M", "color": "Red"}
    total_price = Column(Numeric(10, 2), nullable=False)

    # Order lifecycle - simple COD pipeline
    # pending -> confirmed -> shipped -> delivered  (or cancelled at any point)
    status = Column(String(30), nullable=False, default="pending", index=True)
    notes = Column(String(500), nullable=True)

    # Notification tracking
    telegram_notified = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    product = relationship("Product", lazy="joined")
