from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from utils.db import Base

class StockAlert(Base):
    __tablename__ = "stock_alerts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    alert_type = Column(String(50), nullable=False, default="low_stock")  # e.g., "low_stock", "out_of_stock"
    message = Column(String(500), nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    product = relationship("Product", back_populates="stock_alerts")
    notifications = relationship("Notification", back_populates="stock_alert")

    def __repr__(self):
        return f"<StockAlert(id={self.id}, product_id={self.product_id}, resolved={self.is_resolved})>"