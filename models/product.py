from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.db import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    name = Column(String(200), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    quantity_in_stock = Column(Integer, nullable=False, default=0)
    minimum_stock_level = Column(Integer, nullable=False, default=10)
    
    # Store images as JSON array
    image_urls = Column(String(2500), nullable=True)  # JSON string of URLs
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    category = relationship("Category", back_populates="products")
    admin = relationship("Admin", back_populates="products")
    bill_items = relationship("BillItem", back_populates="product")
    stock_alerts = relationship(
        "StockAlert", 
        back_populates="product", 
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}')>"