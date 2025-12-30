from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from utils.db import Base


class BillItem(Base):
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"),
                        nullable=True)  # change nullable to true
    # Store product name at time of purchase
    product_name = Column(String(200), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # NEW: Store variants as JSON string
    selected_variants = Column(Text, nullable=True)
    # Relationships
    bill = relationship("Bill", back_populates="bill_items")
    product = relationship("Product", back_populates="bill_items")

    def __repr__(self):
        return f"<BillItem(id={self.id}, product='{self.product_name}', qty={self.quantity})>"
