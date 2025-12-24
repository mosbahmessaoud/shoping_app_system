from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from utils.db import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    bill_number = Column(String(50), unique=True, nullable=False, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_paid = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_remaining = Column(Numeric(10, 2), nullable=False, default=0.00)
    status = Column(String(20), nullable=False,
                    default="not paid")  # "paid" or "not paid"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    notification_sent = Column(Boolean, default=False)

    # Relationships
    client = relationship("Client", back_populates="bills")
    bill_items = relationship(
        "BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship(
        "Payment", back_populates="bill", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="bill")

    def __repr__(self):
        return f"<Bill(id={self.id}, bill_number='{self.bill_number}', status='{self.status}')>"
