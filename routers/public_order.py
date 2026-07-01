# routers/public_order.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from decimal import Decimal
import json
import logging

from models.ecommerce_order import EcommerceOrder, DeliveryStatus
from models.product import Product
from schemas.ecommerce_order import (
    EcommerceOrderCreate,
    EcommerceOrderAdminUpdate,
    EcommerceOrderResponse,
    EcommerceOrderSummary,
    EcommerceOrderCreatedResponse,
    OrderTrackingResponse,
)
from utils.db import get_db
from utils.auth import get_current_admin
from utils.wilaya_data import (
    get_all_wilayas,
    get_communes_by_wilaya,
    get_wilaya_by_id,
    get_commune_by_id,
)
from utils.telegram_service import send_new_order_telegram_alert
from utils.tracking import generate_tracking_code, generate_tracking_assets

from sqlalchemy.orm import Session
from sqlalchemy import case, func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public Storefront"])

_TRACKING_CODE_MAX_RETRIES = 10


# ── Location lookups ──────────────────────────────────────────────────────────


@router.get("/locations/wilayas")
def list_wilayas():
    return get_all_wilayas()


@router.get("/locations/wilayas/{wilaya_id}/baladias")
def list_baladias_for_wilaya(wilaya_id: int):
    wilaya = get_wilaya_by_id(wilaya_id)
    if not wilaya:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wilaya non trouvée"
        )
    return get_communes_by_wilaya(wilaya_id)


# ── Public products ───────────────────────────────────────────────────────────


@router.get("/products")
def list_public_products(
    skip: int = 0,
    limit: int = 50,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.is_active == True)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    priority = case(
        (Product.quantity_in_stock == 0, 2),
        (Product.is_sold == True, 0),
        else_=1,
    )
    return query.order_by(priority, Product.id).offset(skip).limit(limit).all()


@router.get("/products/{product_id}")
def get_public_product(product_id: int, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_active == True)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé"
        )
    return product


# ── Order creation ────────────────────────────────────────────────────────────


@router.post(
    "/orders",
    response_model=EcommerceOrderCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_public_order(
    order_data: EcommerceOrderCreate, db: Session = Depends(get_db)
):
    # 1. Validate product
    product = db.query(Product).filter(Product.id == order_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé"
        )
    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce produit n'est plus disponible",
        )
    if product.quantity_in_stock < order_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuffisant. Quantité disponible: {product.quantity_in_stock}",
        )

    # 2. Validate location
    wilaya = get_wilaya_by_id(order_data.wilaya_id)
    if not wilaya:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Wilaya invalide"
        )
    baladia = get_commune_by_id(order_data.baladia_id, wilaya_id=order_data.wilaya_id)
    if not baladia:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baladia invalide pour cette wilaya",
        )

    # 3. Price
    unit_price = product.price
    total_price = (unit_price * order_data.quantity).quantize(Decimal("0.01"))
    selected_variants_json = (
        json.dumps(order_data.selected_variants, ensure_ascii=False)
        if order_data.selected_variants
        else None
    )

    # 4. Generate unique tracking code
    tracking_code = None
    for _ in range(_TRACKING_CODE_MAX_RETRIES):
        candidate = generate_tracking_code()
        exists = (
            db.query(EcommerceOrder)
            .filter(EcommerceOrder.tracking_code == candidate)
            .first()
        )
        if not exists:
            tracking_code = candidate
            break

    if not tracking_code:
        logger.error("Could not generate a unique tracking code after max retries")

    # 5. Create order — delivery_status starts at not_shipped (default)
    new_order = EcommerceOrder(
        full_name=order_data.full_name,
        phone_number=order_data.phone_number,
        wilaya_id=wilaya["wilaya_id"],
        wilaya_name=wilaya["wilaya_name_latin"],
        baladia_id=baladia["commune_id"],
        baladia_name=baladia["commune_name_latin"],
        address_details=order_data.address_details,
        product_id=product.id,
        product_name_snapshot=product.name,
        unit_price_snapshot=unit_price,
        quantity=order_data.quantity,
        selected_variants=selected_variants_json,
        total_price=total_price,
        tracking_code=tracking_code,
        # delivery_status defaults to not_shipped via model default
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 6. Telegram notification
    try:
        sent = send_new_order_telegram_alert(new_order)
        if sent:
            new_order.telegram_notified = True
            db.commit()
    except Exception as e:
        logger.error(f"Telegram alert error for order #{new_order.id}: {e}")

    # 7. QR assets
    assets = (
        generate_tracking_assets(new_order.tracking_code)
        if new_order.tracking_code
        else {"tracking_code": "", "qr_code_base64": "", "tracking_url": ""}
    )

    return EcommerceOrderCreatedResponse(
        message="Commande passée avec succès. Nous vous contacterons bientôt.",
        order_id=new_order.id,
        total_price=total_price,
        tracking_code=assets["tracking_code"],
        qr_code_base64=assets["qr_code_base64"],
        tracking_url=assets["tracking_url"],
    )


# ── Public tracking ───────────────────────────────────────────────────────────


@router.get("/track", response_model=OrderTrackingResponse)
def track_order(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    code = code.strip().upper()
    order = (
        db.query(EcommerceOrder).filter(EcommerceOrder.tracking_code == code).first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code de suivi introuvable. Vérifiez le code et réessayez.",
        )
    return OrderTrackingResponse(
        tracking_code=order.tracking_code,
        order_id=order.id,
        product_name=order.product_name_snapshot,
        wilaya_name=order.wilaya_name,
        baladia_name=order.baladia_name,
        quantity=order.quantity,
        delivery_status=order.delivery_status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# ── Admin management ──────────────────────────────────────────────────────────


@router.get(
    "/admin/orders",
    response_model=List[EcommerceOrderResponse],
    tags=["Public Storefront - Admin"],
)
def get_all_ecommerce_orders(
    skip: int = 0,
    limit: int = 100,
    delivery_status_filter: Optional[DeliveryStatus] = None,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(EcommerceOrder)
    if delivery_status_filter:
        query = query.filter(EcommerceOrder.delivery_status == delivery_status_filter)
    return (
        query.order_by(EcommerceOrder.created_at.desc()).offset(skip).limit(limit).all()
    )


@router.get(
    "/admin/orders/{order_id}",
    response_model=EcommerceOrderResponse,
    tags=["Public Storefront - Admin"],
)
def get_ecommerce_order_by_id(
    order_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    order = db.query(EcommerceOrder).filter(EcommerceOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée"
        )
    return order


@router.patch(
    "/admin/orders/{order_id}",
    response_model=EcommerceOrderResponse,
    tags=["Public Storefront - Admin"],
)
def update_ecommerce_order(
    order_id: int,
    update_data: EcommerceOrderAdminUpdate,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    order = db.query(EcommerceOrder).filter(EcommerceOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée"
        )
    if update_data.delivery_status is not None:
        order.delivery_status = update_data.delivery_status
    if update_data.notes is not None:
        order.notes = update_data.notes
    db.commit()
    db.refresh(order)
    return order


@router.delete(
    "/admin/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Public Storefront - Admin"],
)
def delete_ecommerce_order(
    order_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    order = db.query(EcommerceOrder).filter(EcommerceOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée"
        )
    db.delete(order)
    db.commit()
    return None
