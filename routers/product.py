from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from models.product import Product
from models.category import Category
from schemas.product import (
    ProductCount, ProductCreate, ProductUpdate, 
    ProductResponse, ProductWithCategory, 
    ProductStockStatus, StockUpdate
)
from utils.db import get_db
from utils.auth import get_current_admin
from utils.stock_manager import check_and_create_stock_alert

router = APIRouter(prefix="/product", tags=["Product"])


@router.post("/", response_model=ProductResponse, 
             status_code=status.HTTP_201_CREATED, 
             dependencies=[Depends(get_current_admin)])
def create_product(
    product_data: ProductCreate,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new product (admin only)"""
    
    category = db.query(Category).filter(
        Category.id == product_data.category_id
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    product_dict = product_data.dict(exclude={'category_id', 'image_urls'})
    new_product = Product(
        **product_dict,
        category_id=product_data.category_id,
        admin_id=current_admin.id,
        image_urls=json.dumps(product_data.image_urls)
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    check_and_create_stock_alert(db, new_product)
    
    return _format_product_response(new_product)


@router.get("/count", response_model=ProductCount)
def get_product_count(db: Session = Depends(get_db)):
    """Get total product count"""
    count = db.query(Product).count()
    return {"count": count}


@router.get("/", response_model=List[ProductWithCategory])
def get_all_products(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all products"""
    
    query = db.query(Product)
    
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    products = query.offset(skip).limit(limit).all()
    
    return [
        ProductWithCategory(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            quantity_in_stock=p.quantity_in_stock,
            minimum_stock_level=p.minimum_stock_level,
            image_urls=json.loads(p.image_urls) if p.image_urls else [],
            category_id=p.category_id,
            admin_id=p.admin_id,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
            category_name=p.category.name
        )
        for p in products
    ]


@router.get("/low-stock", response_model=List[ProductStockStatus])
def get_low_stock_products(
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get low stock products (admin only)"""
    
    products = db.query(Product).filter(
        Product.quantity_in_stock <= Product.minimum_stock_level
    ).all()

    result = []
    for p in products:
        percentage = (
            (p.quantity_in_stock / p.minimum_stock_level * 100) 
            if p.minimum_stock_level > 0 else 0
        )
        result.append(ProductStockStatus(
            id=p.id,
            name=p.name,
            quantity_in_stock=p.quantity_in_stock,
            minimum_stock_level=p.minimum_stock_level,
            is_low_stock=True,
            stock_percentage=round(percentage, 2)
        ))

    return result


@router.get("/{product_id}", response_model=ProductWithCategory)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return ProductWithCategory(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        quantity_in_stock=product.quantity_in_stock,
        minimum_stock_level=product.minimum_stock_level,
        image_urls=json.loads(product.image_urls) if product.image_urls else [],
        category_id=product.category_id,
        admin_id=product.admin_id,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        category_name=product.category.name
    )


@router.put("/{product_id}", response_model=ProductResponse,  
            dependencies=[Depends(get_current_admin)])
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update product (admin only)"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if product_data.category_id and product_data.category_id != product.category_id:
        category = db.query(Category).filter(
            Category.id == product_data.category_id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

    update_data = product_data.dict(exclude_unset=True)
    
    if 'image_urls' in update_data:
        update_data['image_urls'] = json.dumps(update_data['image_urls'])
    
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    check_and_create_stock_alert(db, product)
    
    return _format_product_response(product)


@router.patch("/{product_id}/stock", response_model=ProductResponse, 
              dependencies=[Depends(get_current_admin)])
def update_product_stock(
    product_id: int,
    stock_update: StockUpdate,
    db: Session = Depends(get_db)
):
    """Update product stock (admin only)"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if stock_update.quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity cannot be negative"
        )

    product.quantity_in_stock = stock_update.quantity
    db.commit()
    db.refresh(product)
    check_and_create_stock_alert(db, product)
    
    return _format_product_response(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, 
               dependencies=[Depends(get_current_admin)])
def delete_product(
    product_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete product (admin only)"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    db.delete(product)
    db.commit()
    return None


def _format_product_response(product: Product) -> ProductResponse:
    """Helper to format product response with parsed image URLs"""
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        quantity_in_stock=product.quantity_in_stock,
        minimum_stock_level=product.minimum_stock_level,
        image_urls=json.loads(product.image_urls) if product.image_urls else [],
        category_id=product.category_id,
        admin_id=product.admin_id,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at
    )