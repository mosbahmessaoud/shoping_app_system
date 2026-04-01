from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from utils.db import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="admin", cascade="all, delete-orphan") # one to many "admin to products" creates
    payments = relationship("Payment", back_populates="admin") # one to many "admi to payment" processes
    notifications = relationship("Notification", back_populates="admin") # one to many "admin to notification " receives

    def __repr__(self):
        return f"<Admin(id={self.id}, username='{self.username}', email='{self.email}')>"