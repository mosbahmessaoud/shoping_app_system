# routers/public_order.py  (UPDATED — tracking_code generation + /track endpoint)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from decimal import Decimal
import json
import logging

from models.ecommerce_order import EcommerceOrder
from models.product import Product
from schemas.ecommerce_order import (
    EcommerceOrderCreate,
    EcommerceOrderUpdate,
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
from sqlalchemy import case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public Storefront"])

# Max retries when a generated tracking code collides with an existing one
_TRACKING_CODE_MAX_RETRIES = 10


# ============================================================
# LOCATION LOOKUPS
# ============================================================


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


# ============================================================
# PUBLIC PRODUCTS
# ============================================================


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


# ============================================================
# ORDER CREATION  (public, no auth)
# ============================================================


@router.post(
    "/orders",
    response_model=EcommerceOrderCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_public_order(
    order_data: EcommerceOrderCreate, db: Session = Depends(get_db)
):
    """
    Create a COD order from the public storefront.
    Returns a tracking code + QR code PNG (base64) in the response
    so the customer can save them immediately on the confirmation page.
    """
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

    # 4. Generate unique tracking code (retry on rare collision)
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
        # Extremely unlikely — log and continue without a code rather than blocking the order
        logger.error("Could not generate a unique tracking code after max retries")

    # 5. Create order
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
        status="pending",
        tracking_code=tracking_code,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 6. Telegram notification (non-blocking)
    try:
        sent = send_new_order_telegram_alert(new_order)
        if sent:
            new_order.telegram_notified = True
            db.commit()
    except Exception as e:
        logger.error(f"Telegram alert error for order #{new_order.id}: {e}")

    # 7. Generate QR assets  (done after commit so order_id is available)
    assets = (
        generate_tracking_assets(new_order.tracking_code)
        if new_order.tracking_code
        else {
            "tracking_code": "",
            "qr_code_base64": "",
            "tracking_url": "",
        }
    )

    return EcommerceOrderCreatedResponse(
        message="Commande passée avec succès. Nous vous contacterons bientôt.",
        order_id=new_order.id,
        total_price=total_price,
        tracking_code=assets["tracking_code"],
        qr_code_base64=assets["qr_code_base64"],
        tracking_url=assets["tracking_url"],
    )


# ============================================================
# PUBLIC ORDER TRACKING  (no auth — anyone with the code can check)
# ============================================================


@router.get("/track", response_model=OrderTrackingResponse)
def track_order(
    code: str = Query(
        ...,
        description="Tracking code printed on the customer's receipt, e.g. AB-4829-KT",
    ),
    db: Session = Depends(get_db),
):
    """
    Public endpoint — customers enter their tracking code (or scan their QR code)
    to check where their order is.

    Returns only delivery-relevant info — no phone number, no price, no internal notes.
    """
    # Normalize: uppercase + strip whitespace so "ab-4829-kt" works too
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
        status=order.status,
        delivery_status=order.delivery_status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# ============================================================
# ADMIN MANAGEMENT  (auth required — unchanged)
# ============================================================


@router.get(
    "/admin/orders",
    response_model=List[EcommerceOrderResponse],
    tags=["Public Storefront - Admin"],
)
def get_all_ecommerce_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(EcommerceOrder)
    if status_filter:
        query = query.filter(EcommerceOrder.status == status_filter)
    return (
        query.order_by(EcommerceOrder.created_at.desc()).offset(skip).limit(limit).all()
    )


@router.get(
    "/admin/orders/summary",
    response_model=EcommerceOrderSummary,
    tags=["Public Storefront - Admin"],
)
def get_ecommerce_orders_summary(
    current_admin=Depends(get_current_admin), db: Session = Depends(get_db)
):
    total = db.query(EcommerceOrder).count()
    pending = (
        db.query(EcommerceOrder).filter(EcommerceOrder.status == "pending").count()
    )
    confirmed = (
        db.query(EcommerceOrder).filter(EcommerceOrder.status == "confirmed").count()
    )
    shipped = (
        db.query(EcommerceOrder).filter(EcommerceOrder.status == "shipped").count()
    )
    delivered = (
        db.query(EcommerceOrder).filter(EcommerceOrder.status == "delivered").count()
    )
    cancelled = (
        db.query(EcommerceOrder).filter(EcommerceOrder.status == "cancelled").count()
    )

    return EcommerceOrderSummary(
        total_orders=total,
        pending_orders=pending,
        confirmed_orders=confirmed,
        shipped_orders=shipped,
        delivered_orders=delivered,
        cancelled_orders=cancelled,
        not_called_orders=0,
        confirmed_by_phone_orders=0,
        cancelled_by_phone_orders=0,
        unreachable_orders=0,
        not_shipped_orders=0,
        in_delivery_orders=0,
        delivered_orders_delivery=0,
        returned_orders=0,
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
    update_data: EcommerceOrderUpdate,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    order = db.query(EcommerceOrder).filter(EcommerceOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée"
        )
    if update_data.status is not None:
        order.status = update_data.status
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
