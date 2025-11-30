from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from utils.db import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    amount_paid = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=True)  # e.g., "cash", "bank transfer", etc.
    notes = Column(String(500), nullable=True)
    payment_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bill = relationship("Bill", back_populates="payments")
    admin = relationship("Admin", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, bill_id={self.bill_id}, amount={self.amount_paid})>"