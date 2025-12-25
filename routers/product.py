from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from models.product import Product
from models.category import Category
from schemas.product import (
    ProductCount, ProductCreate, ProductUpdate,
    ProductResponse, ProductVariant, ProductWithCategory,
    ProductStockStatus, StockUpdate
)
from utils.db import get_db
from utils.auth import get_current_admin
from utils.stock_manager import check_and_create_stock_alert

import cloudinary.uploader
import re

from datetime import datetime, timedelta
from sqlalchemy import func, extract

router = APIRouter(prefix="/product", tags=["Product"])


def extract_public_id_from_url(url: str) -> Optional[str]:
    """Extract Cloudinary public_id from URL"""
    # Example URL: https://res.cloudinary.com/cloud-name/image/upload/v1234567890/products/abc123.jpg
    # public_id: products/abc123
    match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.[^.]+)?$', url)
    if match:
        return match.group(1)
    return None


def delete_cloudinary_images(image_urls: List[str]) -> dict:
    """Delete multiple images from Cloudinary"""
    deleted = []
    failed = []

    for url in image_urls:
        public_id = extract_public_id_from_url(url)
        if not public_id:
            failed.append({"url": url, "error": "Invalid URL format"})
            continue

        try:
            result = cloudinary.uploader.destroy(public_id)
            if result.get('result') == 'ok':
                deleted.append(public_id)
            else:
                failed.append(
                    {"public_id": public_id, "result": result.get('result')})
        except Exception as e:
            failed.append({"public_id": public_id, "error": str(e)})

    return {"deleted": deleted, "failed": failed}


# Update the create_product endpoint to handle barcode
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

    # Check if barcode already exists
    if product_data.barcode:
        existing_product = db.query(Product).filter(
            Product.barcode == product_data.barcode
        ).first()
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Barcode already exists for product: {existing_product.name}"
            )

    # NEW: Handle multiple variants
    variants_json = None
    if product_data.variants:
        variants_json = json.dumps(product_data.variants.dict())

    product_dict = product_data.dict(exclude={'category_id', 'image_urls'})
    new_product = Product(
        **product_dict,
        category_id=product_data.category_id,
        admin_id=current_admin.id,
        image_urls=json.dumps(product_data.image_urls),
        variants=variants_json  # NEW

    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    check_and_create_stock_alert(db, new_product)

    return _format_product_response(new_product)


# @router.post("/", response_model=ProductResponse,
#              status_code=status.HTTP_201_CREATED,
#              dependencies=[Depends(get_current_admin)])
# def create_product(
#     product_data: ProductCreate,
#     current_admin=Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ):
#     """Create a new product (admin only)"""

#     category = db.query(Category).filter(
#         Category.id == product_data.category_id
#     ).first()
#     if not category:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Category not found"
#         )

#     product_dict = product_data.dict(exclude={'category_id', 'image_urls'})
#     new_product = Product(
#         **product_dict,
#         category_id=product_data.category_id,
#         admin_id=current_admin.id,
#         image_urls=json.dumps(product_data.image_urls)
#     )

#     db.add(new_product)
#     db.commit()
#     db.refresh(new_product)
#     check_and_create_stock_alert(db, new_product)

#     return _format_product_response(new_product)


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
    result = []
    for p in products:
        variants_data = None
        if p.variants:
            try:
                variants_dict = json.loads(p.variants)
                variants_data = ProductVariant(**variants_dict)
            except (json.JSONDecodeError, ValueError):
                pass

        result.append(ProductWithCategory(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            quantity_in_stock=p.quantity_in_stock,
            minimum_stock_level=p.minimum_stock_level,
            image_urls=json.loads(p.image_urls) if p.image_urls else [],
            category_id=p.category_id,
            admin_id=p.admin_id,
            barcode=p.barcode,
            variants=variants_data,
            is_sold=p.is_sold,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
            category_name=p.category.name
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

    variants_data = None
    if product.variants:
        try:
            variants_dict = json.loads(product.variants)
            variants_data = ProductVariant(**variants_dict)
        except (json.JSONDecodeError, ValueError):
            pass

    return ProductWithCategory(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        quantity_in_stock=product.quantity_in_stock,
        minimum_stock_level=product.minimum_stock_level,
        image_urls=json.loads(
            product.image_urls) if product.image_urls else [],
        category_id=product.category_id,
        admin_id=product.admin_id,
        barcode=product.barcode,
        is_sold=product.is_sold,
        variants=variants_data,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        category_name=product.category.name
    )


@router.get("/barcode/{barcode}", response_model=ProductWithCategory)
def get_product_by_barcode(barcode: str, db: Session = Depends(get_db)):
    """Get product by barcode"""

    product = db.query(Product).filter(Product.barcode == barcode).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found with this barcode"
        )

    variants_data = None
    if product.variants:
        try:
            variants_dict = json.loads(product.variants)
            variants_data = ProductVariant(**variants_dict)
        except (json.JSONDecodeError, ValueError):
            pass

    return ProductWithCategory(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        quantity_in_stock=product.quantity_in_stock,
        minimum_stock_level=product.minimum_stock_level,
        image_urls=json.loads(
            product.image_urls) if product.image_urls else [],
        category_id=product.category_id,
        admin_id=product.admin_id,
        barcode=product.barcode,
        variants=variants_data,
        is_sold=product.is_sold,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        category_name=product.category.name
    )


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


# @router.put("/{product_id}", response_model=ProductResponse,
#             dependencies=[Depends(get_current_admin)])
# def update_product(
#     product_id: int,
#     product_data: ProductUpdate,
#     current_admin=Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ):
#     """Update product (admin only)"""

#     product = db.query(Product).filter(Product.id == product_id).first()
#     if not product:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Product not found"
#         )

#     if product_data.category_id and product_data.category_id != product.category_id:
#         category = db.query(Category).filter(
#             Category.id == product_data.category_id
#         ).first()
#         if not category:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Category not found"
#             )

#     update_data = product_data.dict(exclude_unset=True)

#     if 'image_urls' in update_data:
#         update_data['image_urls'] = json.dumps(update_data['image_urls'])

#     for field, value in update_data.items():
#         setattr(product, field, value)

#     db.commit()
#     db.refresh(product)
#     check_and_create_stock_alert(db, product)

#     return _format_product_response(product)
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

    # Handle image updates: delete old images that are being replaced
    if 'image_urls' in update_data:
        old_urls = json.loads(product.image_urls) if product.image_urls else []
        new_urls = update_data['image_urls']

        # Find images that are being removed
        urls_to_delete = [url for url in old_urls if url not in new_urls]

        if urls_to_delete:
            deletion_result = delete_cloudinary_images(urls_to_delete)
            # Log failures
            if deletion_result['failed']:
                print(
                    f"Failed to delete old images: {deletion_result['failed']}")

        update_data['image_urls'] = json.dumps(new_urls)

    # NEW: Handle variants update
    if 'variants' in update_data:
        if update_data['variants'] is not None:
            update_data['variants'] = json.dumps(update_data['variants'])
        # If variants is explicitly set to None, it will clear the variants

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


# @router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT,
#                dependencies=[Depends(get_current_admin)])
# def delete_product(
#     product_id: int,
#     current_admin=Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ):
#     """Delete product (admin only)"""

#     product = db.query(Product).filter(Product.id == product_id).first()
#     if not product:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Product not found"
#         )

#     db.delete(product)
#     db.commit()
#     return None

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(get_current_admin)])
def delete_product(
    product_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete product and its images from Cloudinary (admin only)"""

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Delete images from Cloudinary before deleting product
    image_urls = json.loads(product.image_urls) if product.image_urls else []
    if image_urls:
        deletion_result = delete_cloudinary_images(image_urls)
        # Log failures but don't block deletion
        if deletion_result['failed']:
            print(f"Failed to delete some images: {deletion_result['failed']}")

    db.delete(product)
    db.commit()
    return None


# Update _format_product_response to include barcode
def _format_product_response(product: Product) -> ProductResponse:
    """Helper to format product response with parsed image URLs"""
    from schemas.product import ProductVariant  # Import at function level to avoid circular import

    variants_data = None
    if product.variants:
        try:
            variants_dict = json.loads(product.variants)
            variants_data = ProductVariant(**variants_dict)
        except (json.JSONDecodeError, ValueError):
            pass

    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        quantity_in_stock=product.quantity_in_stock,
        minimum_stock_level=product.minimum_stock_level,
        image_urls=json.loads(
            product.image_urls) if product.image_urls else [],
        category_id=product.category_id,
        admin_id=product.admin_id,
        barcode=product.barcode,  # NEW
        is_sold=product.is_sold,  # NEW
        variants=variants_data,  # NEW
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at
    )

# def _format_product_response(product: Product) -> ProductResponse:
#     """Helper to format product response with parsed image URLs"""
#     return ProductResponse(
#         id=product.id,
#         name=product.name,
#         description=product.description,
#         price=product.price,
#         quantity_in_stock=product.quantity_in_stock,
#         minimum_stock_level=product.minimum_stock_level,
#         image_urls=json.loads(
#             product.image_urls) if product.image_urls else [],
#         category_id=product.category_id,
#         admin_id=product.admin_id,
#         is_active=product.is_active,
#         created_at=product.created_at,
#         updated_at=product.updated_at
#     )


# new endpoint to delete a specific image from a product

@router.delete("/{product_id}/images", response_model=ProductResponse,
               dependencies=[Depends(get_current_admin)])
def delete_product_image(
    product_id: int,
    image_url: str,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete specific image from product (admin only)"""

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Get current images
    current_urls = json.loads(product.image_urls) if product.image_urls else []

    # Check if image exists
    if image_url not in current_urls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found in product"
        )

    # Delete from Cloudinary
    deletion_result = delete_cloudinary_images([image_url])

    if deletion_result['failed']:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image from Cloudinary: {deletion_result['failed']}"
        )

    # Remove from product
    current_urls.remove(image_url)
    product.image_urls = json.dumps(current_urls)

    db.commit()
    db.refresh(product)

    return _format_product_response(product)


@router.post("/generate-barcode", response_model=dict)
def generate_barcode(db: Session = Depends(get_db)):
    """Generate a unique EAN-13 barcode for a new product"""
    import random

    while True:
        # Generate 12 random digits
        barcode_base = ''.join([str(random.randint(0, 9)) for _ in range(12)])

        # Calculate EAN-13 check digit
        odd_sum = sum(int(barcode_base[i]) for i in range(0, 12, 2))
        even_sum = sum(int(barcode_base[i]) for i in range(1, 12, 2))
        total = odd_sum + (even_sum * 3)
        check_digit = (10 - (total % 10)) % 10

        barcode = barcode_base + str(check_digit)

        # Check if barcode already exists
        existing = db.query(Product).filter(Product.barcode == barcode).first()
        if not existing:
            return {"barcode": barcode}


@router.get("/{product_id}/statistics", response_model=dict,
            dependencies=[Depends(get_current_admin)])
def get_product_statistics(
    product_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get product sales statistics (admin only)"""
    from models.bill_item import BillItem
    from models.bill import Bill

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)
    year_start = datetime(now.year, 1, 1)

    # Daily sales
    daily = db.query(
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= today_start
    ).first()

    # Monthly sales
    monthly = db.query(
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= month_start
    ).first()

    # Yearly sales
    yearly = db.query(
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= year_start
    ).first()

    return {
        'product_id': product_id,
        'product_name': product.name,
        'daily_sales': int(daily.quantity or 0),
        'daily_revenue': float(daily.revenue or 0),
        'monthly_sales': int(monthly.quantity or 0),
        'monthly_revenue': float(monthly.revenue or 0),
        'yearly_sales': int(yearly.quantity or 0),
        'yearly_revenue': float(yearly.revenue or 0),
        'current_stock': product.quantity_in_stock,
        'stock_value': float(product.price * product.quantity_in_stock),
    }


@router.get("/{product_id}/statistics/detailed", response_model=dict,
            dependencies=[Depends(get_current_admin)])
def get_product_detailed_statistics(
    product_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed product sales statistics with hourly/daily/monthly breakdown (admin only)"""
    from models.bill_item import BillItem
    from models.bill import Bill

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)
    year_start = datetime(now.year, 1, 1)

    # Today's sales by hour
    today_sales = db.query(
        extract('hour', Bill.created_at).label('hour'),
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= today_start
    ).group_by('hour').all()

    # Month's sales by day
    month_sales = db.query(
        extract('day', Bill.created_at).label('day'),
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= month_start
    ).group_by('day').all()

    # Year's sales by month
    year_sales = db.query(
        extract('month', Bill.created_at).label('month'),
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= year_start
    ).group_by('month').all()

    # Calculate totals
    daily_total = db.query(
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= today_start
    ).first()

    monthly_total = db.query(
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= month_start
    ).first()

    yearly_total = db.query(
        func.sum(BillItem.quantity).label('quantity'),
        func.sum(BillItem.subtotal).label('revenue')
    ).join(Bill).filter(
        BillItem.product_id == product_id,
        Bill.created_at >= year_start
    ).first()

    return {
        'product_id': product_id,
        'product_name': product.name,
        'today': {
            'total_quantity': int(daily_total.quantity or 0),
            'total_revenue': float(daily_total.revenue or 0),
            'data': [
                {
                    'hour': int(item.hour),
                    'quantity': int(item.quantity or 0),
                    'revenue': float(item.revenue or 0)
                }
                for item in today_sales
            ]
        },
        'month': {
            'total_quantity': int(monthly_total.quantity or 0),
            'total_revenue': float(monthly_total.revenue or 0),
            'data': [
                {
                    'day': int(item.day),
                    'quantity': int(item.quantity or 0),
                    'revenue': float(item.revenue or 0)
                }
                for item in month_sales
            ]
        },
        'year': {
            'total_quantity': int(yearly_total.quantity or 0),
            'total_revenue': float(yearly_total.revenue or 0),
            'data': [
                {
                    'month': int(item.month),
                    'quantity': int(item.quantity or 0),
                    'revenue': float(item.revenue or 0)
                }
                for item in year_sales
            ]
        },
        'current_stock': product.quantity_in_stock,
        'stock_value': float(product.price * product.quantity_in_stock),
    }


@router.get("/{product_id}/purchases/timeline", response_model=dict,
            dependencies=[Depends(get_current_admin)])
def get_product_purchases_timeline(
    product_id: int,
    period: str = 'week',  # 'week', 'month', 'year'
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get product purchase count timeline (admin only)"""
    from models.bill_item import BillItem
    from models.bill import Bill

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    now = datetime.now()

    if period == 'week':
        start_date = now - timedelta(days=6)
        results = db.query(
            func.date(Bill.created_at).label('date'),
            func.count(BillItem.id).label('purchases')
        ).join(Bill).filter(
            BillItem.product_id == product_id,
            Bill.created_at >= start_date
        ).group_by(func.date(Bill.created_at)).all()

        return {
            'period': period,
            'data': [
                {
                    'date': str(item.date),
                    'purchases': int(item.purchases)
                }
                for item in results
            ]
        }

    elif period == 'month':
        start_date = datetime(now.year, now.month, 1)
        results = db.query(
            func.date(Bill.created_at).label('date'),
            func.count(BillItem.id).label('purchases')
        ).join(Bill).filter(
            BillItem.product_id == product_id,
            Bill.created_at >= start_date
        ).group_by(func.date(Bill.created_at)).all()

        return {
            'period': period,
            'data': [
                {
                    'date': str(item.date),
                    'purchases': int(item.purchases)
                }
                for item in results
            ]
        }

    elif period == 'year':
        start_date = datetime(now.year, 1, 1)
        results = db.query(
            extract('month', Bill.created_at).label('month'),
            func.count(BillItem.id).label('purchases')
        ).join(Bill).filter(
            BillItem.product_id == product_id,
            Bill.created_at >= start_date
        ).group_by('month').all()

        return {
            'period': period,
            'data': [
                {
                    'month': int(item.month),
                    'purchases': int(item.purchases)
                }
                for item in results
            ]
        }
