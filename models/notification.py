from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from utils.db import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True)
    stock_alert_id = Column(Integer, ForeignKey("stock_alerts.id"), nullable=True)
    notification_type = Column(String(50), nullable=False)  # e.g., "new_bill", "stock_alert", "payment_received"
    channel = Column(String(20), nullable=False)  # "email" or "whatsapp"
    message = Column(String(1000), nullable=False)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    admin = relationship("Admin", back_populates="notifications")
    client = relationship("Client", back_populates="notifications")
    bill = relationship("Bill", back_populates="notifications")
    stock_alert = relationship("StockAlert", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.notification_type}', sent={self.is_sent})>"