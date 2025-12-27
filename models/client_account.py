
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from utils.db import Base


class ClientAccount(Base):
    __tablename__ = "client_accounts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), unique=True, nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0.00)
    total_paid = Column(Numeric(15, 2), nullable=False, default=0.00)
    total_remaining = Column(Numeric(15, 2), nullable=False, default=0.00)
    total_credit = Column(Numeric(15, 2), nullable=False, default=0.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    client = relationship("Client", back_populates="account")

    def __repr__(self):
        return f"<ClientAccount(id={self.id}, client_id={self.client_id}, total_remaining={self.total_remaining})>"



