# routers/store_orders.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from models.ecommerce_order import (
    EcommerceOrder,
    CallingStatus,
    DeliveryStatus,
)
from models.store_user import StoreUser, StoreUserRole
from schemas.ecommerce_order import (
    EcommerceOrderAdminUpdate,
    EcommerceOrderLivreurUpdate,
    EcommerceOrderResponse,
    EcommerceOrderSummary,
)
from utils.db import get_db
from utils.store_auth import get_current_store_user, get_current_store_admin

router = APIRouter(prefix="/store/orders", tags=["Store Dashboard - Orders"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_order_or_404(order_id: int, db: Session) -> EcommerceOrder:
    order = db.query(EcommerceOrder).filter(EcommerceOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commande #{order_id} introuvable",
        )
    return order


def _assert_livreur_can_see(order: EcommerceOrder) -> None:
    if order.is_hidden_from_livreurs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette commande n'est pas accessible",
        )


# ── List orders ───────────────────────────────────────────────────────────────


@router.get("", response_model=List[EcommerceOrderResponse])
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    calling_status_filter: Optional[CallingStatus] = Query(
        None, alias="calling_status"
    ),
    delivery_status_filter: Optional[DeliveryStatus] = Query(
        None, alias="delivery_status"
    ),
    wilaya_id: Optional[int] = Query(None),
    assigned_livreur_id: Optional[int] = Query(None),
    search_phone: Optional[str] = Query(None),
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    query = db.query(EcommerceOrder)

    if current_user.role == StoreUserRole.livreur:
        query = query.filter(EcommerceOrder.is_hidden_from_livreurs == False)

    if calling_status_filter:
        query = query.filter(EcommerceOrder.calling_status == calling_status_filter)
    if delivery_status_filter:
        query = query.filter(EcommerceOrder.delivery_status == delivery_status_filter)
    if wilaya_id is not None:
        query = query.filter(EcommerceOrder.wilaya_id == wilaya_id)
    if assigned_livreur_id is not None:
        query = query.filter(EcommerceOrder.assigned_livreur_id == assigned_livreur_id)
    if search_phone:
        query = query.filter(EcommerceOrder.phone_number.ilike(f"%{search_phone}%"))

    return (
        query.order_by(EcommerceOrder.created_at.desc()).offset(skip).limit(limit).all()
    )


# ── Summary (admin only) ──────────────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=EcommerceOrderSummary,
    tags=["Store Dashboard - Orders (Admin)"],
)
def get_orders_summary(
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    def count(filters) -> int:
        return db.query(func.count(EcommerceOrder.id)).filter(*filters).scalar()

    return EcommerceOrderSummary(
        total_orders=count([]),
        # Delivery axis
        not_shipped_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.not_shipped]
        ),
        in_delivery_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.shipped]
        ),
        delivered_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.delivered]
        ),
        returned_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.returned]
        ),
        cancelled_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.cancelled]
        ),
        # Calling axis
        not_called_orders=count(
            [EcommerceOrder.calling_status == CallingStatus.not_called]
        ),
        confirmed_by_phone_orders=count(
            [EcommerceOrder.calling_status == CallingStatus.confirmed_by_phone]
        ),
        cancelled_by_phone_orders=count(
            [EcommerceOrder.calling_status == CallingStatus.cancelled_by_phone]
        ),
        unreachable_orders=count(
            [EcommerceOrder.calling_status == CallingStatus.unreachable]
        ),
    )


# ── Get single order ──────────────────────────────────────────────────────────


@router.get("/{order_id}", response_model=EcommerceOrderResponse)
def get_order(
    order_id: int,
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    if current_user.role == StoreUserRole.livreur:
        _assert_livreur_can_see(order)
    return order


# ── Update order (admin) ──────────────────────────────────────────────────────


@router.patch("/{order_id}", response_model=EcommerceOrderResponse)
def update_order(
    order_id: int,
    update_data: EcommerceOrderAdminUpdate,
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)

    if current_user.role == StoreUserRole.livreur:
        _assert_livreur_can_see(order)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les livreurs doivent utiliser PATCH /store/orders/{id}/livreur",
        )

    if update_data.delivery_status is not None:
        order.delivery_status = update_data.delivery_status
    if update_data.calling_status is not None:
        order.calling_status = update_data.calling_status
    if update_data.notes is not None:
        order.notes = update_data.notes
    if update_data.is_hidden_from_livreurs is not None:
        order.is_hidden_from_livreurs = update_data.is_hidden_from_livreurs

    if update_data.assigned_livreur_id is not None:
        livreur = (
            db.query(StoreUser)
            .filter(
                StoreUser.id == update_data.assigned_livreur_id,
                StoreUser.role == StoreUserRole.livreur,
                StoreUser.is_active == True,
            )
            .first()
        )
        if not livreur:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Livreur introuvable ou inactif",
            )
        order.assigned_livreur_id = livreur.id
    elif (
        "assigned_livreur_id" in (update_data.model_fields_set or set())
        and update_data.assigned_livreur_id is None
    ):
        order.assigned_livreur_id = None

    db.commit()
    db.refresh(order)
    return order


# ── Livreur-specific update ───────────────────────────────────────────────────


@router.patch("/{order_id}/livreur", response_model=EcommerceOrderResponse)
def livreur_update_order(
    order_id: int,
    update_data: EcommerceOrderLivreurUpdate,
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)

    if current_user.role == StoreUserRole.livreur:
        _assert_livreur_can_see(order)

    if update_data.calling_status is not None:
        order.calling_status = update_data.calling_status
    if update_data.delivery_status is not None:
        order.delivery_status = update_data.delivery_status
    if update_data.livreur_notes is not None:
        order.livreur_notes = update_data.livreur_notes

    db.commit()
    db.refresh(order)
    return order


# ── Hide / unhide (admin only) ────────────────────────────────────────────────


@router.patch(
    "/{order_id}/hide",
    response_model=EcommerceOrderResponse,
    tags=["Store Dashboard - Orders (Admin)"],
)
def toggle_order_visibility(
    order_id: int,
    hide: bool = Query(...),
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    order.is_hidden_from_livreurs = hide
    db.commit()
    db.refresh(order)
    return order


# ── Assign livreur (admin only) ───────────────────────────────────────────────


@router.patch(
    "/{order_id}/assign",
    response_model=EcommerceOrderResponse,
    tags=["Store Dashboard - Orders (Admin)"],
)
def assign_livreur(
    order_id: int,
    livreur_id: Optional[int] = Query(None),
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)

    if livreur_id is not None:
        livreur = (
            db.query(StoreUser)
            .filter(
                StoreUser.id == livreur_id,
                StoreUser.role == StoreUserRole.livreur,
                StoreUser.is_active == True,
            )
            .first()
        )
        if not livreur:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Livreur introuvable ou inactif",
            )
        order.assigned_livreur_id = livreur.id
    else:
        order.assigned_livreur_id = None

    db.commit()
    db.refresh(order)
    return order


# ── Delete (admin only) ───────────────────────────────────────────────────────


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Store Dashboard - Orders (Admin)"],
)
def delete_order(
    order_id: int,
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    db.delete(order)
    db.commit()
    return None
