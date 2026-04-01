from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(15, 2), nullable=False)
    quantity_in_stock = Column(Integer, nullable=False, default=0)
    minimum_stock_level = Column(Integer, nullable=False, default=10)

    barcode = Column(String(100), nullable=True, unique=True, index=True)

    # as a JSON string of URLs
    image_urls = Column(String(2500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # means a is enable to sell or not
    is_sold = Column(Boolean, default=False)

    # JSON string for variant configurations
    variants = Column(Text, nullable=True)

    # Relationships
    # many to one "products to categroy" belongs to
    category = relationship("Category", back_populates="products")
    # many to one "products to admin" managed by
    admin = relationship("Admin", back_populates="products")
    # one to many "product to billitems " ordered in
    bill_items = relationship("BillItem", back_populates="product")
    stock_alerts = relationship(
        "StockAlert",
        back_populates="product",
        cascade="all, delete-orphan"
    )  # one to many "product to stoclalert " triggers

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}')>"
