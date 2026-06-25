# routers/public_order.py
from fastapi import APIRouter, Depends, HTTPException, status
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

# After
from sqlalchemy.orm import Session
from sqlalchemy import case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public Storefront"])


# ============================================================
# LOCATION LOOKUPS (for the storefront's shipping form)
# ============================================================


@router.get("/locations/wilayas")
def list_wilayas():
    """Liste de toutes les wilayas (accès public, pas d'authentification)"""
    return get_all_wilayas()


@router.get("/locations/wilayas/{wilaya_id}/baladias")
def list_baladias_for_wilaya(wilaya_id: int):
    """Liste des baladias (communes) d'une wilaya donnée (accès public)"""
    wilaya = get_wilaya_by_id(wilaya_id)
    if not wilaya:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wilaya non trouvée"
        )
    return get_communes_by_wilaya(wilaya_id)


# ============================================================
# PUBLIC STOREFRONT PRODUCTS (read-only, no auth)
# ============================================================


@router.get("/products")
def list_public_products(
    skip: int = 0,
    limit: int = 50,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Liste des produits actifs pour la vitrine publique.

    Ordering:
      1. In-stock + special offer (is_sold=True)  → top
      2. In-stock regular                          → middle
      3. Out of stock (quantity_in_stock == 0)     → bottom
    """
    query = db.query(Product).filter(Product.is_active == True)

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    priority = case(
        (Product.quantity_in_stock == 0, 2),  # out of stock  → last
        (Product.is_sold == True, 0),  # special offer → first
        else_=1,  # regular stock → middle
    )

    products = query.order_by(priority, Product.id).offset(skip).limit(limit).all()
    return products


@router.get("/products/{product_id}")
def get_public_product(product_id: int, db: Session = Depends(get_db)):
    """Détails d'un produit pour sa page de vente unique (accès public)"""
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
# ORDER CREATION (public, no auth) — the COD lead capture
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
    Créer une commande COD depuis la vitrine publique.
    Aucune authentification requise — c'est le point d'entrée des clients individuels.
    """
    # 1. Validate product exists, is active, and is in stock
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

    # 2. Validate wilaya / baladia
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

    # 3. Compute price snapshot (server-side truth, never trust client price)
    unit_price = product.price
    total_price = (unit_price * order_data.quantity).quantize(Decimal("0.01"))

    selected_variants_json = (
        json.dumps(order_data.selected_variants, ensure_ascii=False)
        if order_data.selected_variants
        else None
    )

    # 4. Create order
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
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 5. Optional Telegram notification — never blocks order success on failure
    try:
        sent = send_new_order_telegram_alert(new_order)
        if sent:
            new_order.telegram_notified = True
            db.commit()
    except Exception as e:
        logger.error(
            f"Unexpected error sending Telegram alert for order #{new_order.id}: {str(e)}"
        )

    return EcommerceOrderCreatedResponse(
        message="Commande passée avec succès. Nous vous contacterons bientôt.",
        order_id=new_order.id,
        total_price=total_price,
    )


# ============================================================
# ADMIN MANAGEMENT (auth required) — separate from B2B Bill flow
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
    """Obtenir toutes les commandes e-commerce (admin seulement)"""
    query = db.query(EcommerceOrder)
    if status_filter:
        query = query.filter(EcommerceOrder.status == status_filter)
    orders = (
        query.order_by(EcommerceOrder.created_at.desc()).offset(skip).limit(limit).all()
    )
    return orders


@router.get(
    "/admin/orders/summary",
    response_model=EcommerceOrderSummary,
    tags=["Public Storefront - Admin"],
)
def get_ecommerce_orders_summary(
    current_admin=Depends(get_current_admin), db: Session = Depends(get_db)
):
    """Résumé des commandes e-commerce par statut (admin seulement)"""
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
    """Obtenir une commande e-commerce par son ID (admin seulement)"""
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
    """Mettre à jour le statut/notes d'une commande e-commerce (admin seulement)"""
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
    """Supprimer une commande e-commerce (admin seulement)"""
    order = db.query(EcommerceOrder).filter(EcommerceOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée"
        )
    db.delete(order)
    db.commit()
    return None
