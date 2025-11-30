from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Stock Alert Base Schema
class StockAlertBase(BaseModel):
    product_id: int
    alert_type: str = Field(default="low_stock", max_length=50)
    message: str = Field(..., max_length=500)

# Stock Alert Create Schema
class StockAlertCreate(StockAlertBase):
    pass

# Stock Alert Update Schema
class StockAlertUpdate(BaseModel):
    is_resolved: bool
    resolved_at: Optional[datetime] = None

# Stock Alert Response Schema
class StockAlertResponse(StockAlertBase):
    id: int
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

# Stock Alert with Product Info
class StockAlertWithProduct(StockAlertResponse):
    product_name: str
    quantity_in_stock: int
    minimum_stock_level: int
    category_name: str

    class Config:
        from_attributes = True

# Stock Alert Summary
class StockAlertSummary(BaseModel):
    total_alerts: int
    unresolved_alerts: int
    resolved_alerts: int
    critical_products: int  # Products with 0 stock

    class Config:
        from_attributes = True