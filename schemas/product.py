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
    is_active: bool = True

    @field_validator('image_urls')
    @classmethod
    def validate_images(cls, v):
        # REMOVED: minimum image requirement
        # Images are now optional (can be empty list)
        if len(v) > 5:
            raise ValueError('Maximum 5 images allowed')
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
    is_active: Optional[bool] = None

    @field_validator('image_urls')
    @classmethod
    def validate_images(cls, v):
        if v is not None:
            # REMOVED: minimum image requirement
            # Images are optional in updates
            if len(v) > 5:
                raise ValueError('Maximum 5 images allowed')
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
