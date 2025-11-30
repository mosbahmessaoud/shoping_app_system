from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Category Base Schema
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

# Category Create Schema
class CategoryCreate(CategoryBase):
    pass

# Category Update Schema
class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

# Category Response Schema
class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Category with Product Count
class CategoryWithCount(CategoryResponse):
    product_count: int = 0

    class Config:
        from_attributes = True