from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    quantity_in_stock: int = Field(..., ge=0)
    minimum_stock_level: int = Field(default=10, ge=0)
    image_urls: List[str] = Field(default=[], max_length=5)
    category_id: int
    barcode: Optional[str] = Field(
        None, max_length=100)  # NEW: Optional barcode
    is_active: bool = True
    is_sold: bool = False

    @field_validator('image_urls')
    @classmethod
    def validate_images(cls, v):
        if len(v) > 5:
            raise ValueError('Maximum 5 images allowed')
        return v

    @field_validator('barcode')
    @classmethod
    def validate_barcode(cls, v):
        if v is not None:
            # Remove whitespace
            v = v.strip()
            if v == '':
                return None
            # Validate length (most barcodes are 8-14 digits)
            if len(v) < 6 or len(v) > 100:
                raise ValueError(
                    'Barcode must be between 6 and 100 characters')
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    quantity_in_stock: Optional[int] = Field(None, ge=0)
    minimum_stock_level: Optional[int] = Field(None, ge=0)
    image_urls: Optional[List[str]] = Field(None, max_length=5)
    category_id: Optional[int] = None
    barcode: Optional[str] = Field(None, max_length=100)  # NEW
    is_active: Optional[bool] = None
    is_sold: Optional[bool] = None

    @field_validator('image_urls')
    @classmethod
    def validate_images(cls, v):
        if v is not None and len(v) > 5:
            raise ValueError('Maximum 5 images allowed')
        return v

    @field_validator('barcode')
    @classmethod
    def validate_barcode(cls, v):
        if v is not None:
            v = v.strip()
            if v == '':
                return None
            if len(v) < 6 or len(v) > 100:
                raise ValueError(
                    'Barcode must be between 6 and 100 characters')
        return v


class ProductCount(BaseModel):
    count: int


class ProductResponse(ProductBase):
    id: int
    admin_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProductWithCategory(ProductResponse):
    category_name: str

    class Config:
        from_attributes = True


class ProductStockStatus(BaseModel):
    id: int
    name: str
    quantity_in_stock: int
    minimum_stock_level: int
    is_low_stock: bool
    stock_percentage: float

    class Config:
        from_attributes = True


class StockUpdate(BaseModel):
    quantity: int
