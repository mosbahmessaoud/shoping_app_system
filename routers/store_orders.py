# routers/store_orders.py
#
# Order management for the website/ecommerce dashboard.
# All routes are mounted under /store/orders
#
# Role matrix:
#
#   Endpoint                           | admin | livreur
#   -----------------------------------|-------|--------
#   GET  /store/orders                 |  ✓    |  ✓ (hidden orders excluded)
#   GET  /store/orders/summary         |  ✓    |  ✗
#   GET  /store/orders/{id}            |  ✓    |  ✓ (if not hidden)
#   PATCH /store/orders/{id}           |  ✓    |  ✓ (livreur fields only)
#   PATCH /store/orders/{id}/hide      |  ✓    |  ✗
#   PATCH /store/orders/{id}/assign    |  ✓    |  ✗
#   DELETE /store/orders/{id}          |  ✓    |  ✗
#
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from models.ecommerce_order import (
    EcommerceOrder,
    OrderStatus,
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
    """Raise 403 if a livreur tries to access a hidden order."""
    if order.is_hidden_from_livreurs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette commande n'est pas accessible",
        )


# ── List orders ───────────────────────────────────────────────────────────────


@router.get("", response_model=List[EcommerceOrderResponse])
def list_orders(
    # Pagination
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    # Filters
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    calling_status_filter: Optional[CallingStatus] = Query(
        None, alias="calling_status"
    ),
    delivery_status_filter: Optional[DeliveryStatus] = Query(
        None, alias="delivery_status"
    ),
    wilaya_id: Optional[int] = Query(None),
    assigned_livreur_id: Optional[int] = Query(None),
    search_phone: Optional[str] = Query(
        None, description="Partial phone number search"
    ),
    # Auth
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """
    List orders for the dashboard.

    - Admin    : sees ALL orders including hidden ones; can filter by any field.
    - Livreur  : sees only non-hidden orders; cannot filter by hidden status.
    """
    query = db.query(EcommerceOrder)

    # ── Visibility gate ───────────────────────────────────────────────────────
    if current_user.role == StoreUserRole.livreur:
        query = query.filter(EcommerceOrder.is_hidden_from_livreurs == False)

    # ── Filters ───────────────────────────────────────────────────────────────
    if status_filter:
        query = query.filter(EcommerceOrder.status == status_filter)
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

    orders = (
        query.order_by(EcommerceOrder.created_at.desc()).offset(skip).limit(limit).all()
    )
    return orders


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
    """
    Aggregate counts across all status axes.
    Used for the dashboard home-page KPI cards.
    Admin only.
    """

    def count(filters) -> int:
        return db.query(func.count(EcommerceOrder.id)).filter(*filters).scalar()

    return EcommerceOrderSummary(
        # Main status
        total_orders=count([]),
        pending_orders=count([EcommerceOrder.status == OrderStatus.pending]),
        confirmed_orders=count([EcommerceOrder.status == OrderStatus.confirmed]),
        shipped_orders=count([EcommerceOrder.status == OrderStatus.shipped]),
        delivered_orders=count([EcommerceOrder.status == OrderStatus.delivered]),
        cancelled_orders=count([EcommerceOrder.status == OrderStatus.cancelled]),
        # Calling status
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
        # Delivery status
        not_shipped_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.not_shipped]
        ),
        in_delivery_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.shipped]
        ),
        delivered_orders_delivery=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.delivered]
        ),
        returned_orders=count(
            [EcommerceOrder.delivery_status == DeliveryStatus.returned]
        ),
    )


# ── Get single order ──────────────────────────────────────────────────────────


@router.get("/{order_id}", response_model=EcommerceOrderResponse)
def get_order(
    order_id: int,
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """
    Get a single order by ID.
    Livreurs are blocked from hidden orders.
    """
    order = _get_order_or_404(order_id, db)
    if current_user.role == StoreUserRole.livreur:
        _assert_livreur_can_see(order)
    return order


# ── Update order (shared endpoint, role-aware) ────────────────────────────────


@router.patch("/{order_id}", response_model=EcommerceOrderResponse)
def update_order(
    order_id: int,
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
    # We accept a raw body and decide which schema to enforce by role
    update_data: EcommerceOrderAdminUpdate = None,
):
    """
    Update an order.

    - Admin   : can update status, calling_status, delivery_status,
                notes, assigned_livreur_id, is_hidden_from_livreurs.
    - Livreur : can ONLY update calling_status, delivery_status, livreur_notes.
                Hidden orders return 403. Livreur cannot touch admin fields.

    Use the appropriate request body for your role (see schema below).
    """
    order = _get_order_or_404(order_id, db)

    if current_user.role == StoreUserRole.livreur:
        _assert_livreur_can_see(order)
        # update_data is typed as AdminUpdate for OpenAPI docs but we ignore
        # admin-only fields — the livreur schema is enforced in the livreur endpoint below.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les livreurs doivent utiliser PATCH /store/orders/{id}/livreur",
        )

    # ── Admin update ──────────────────────────────────────────────────────────
    if update_data.status is not None:
        order.status = update_data.status
    if update_data.calling_status is not None:
        order.calling_status = update_data.calling_status
    if update_data.delivery_status is not None:
        order.delivery_status = update_data.delivery_status
    if update_data.notes is not None:
        order.notes = update_data.notes
    if update_data.is_hidden_from_livreurs is not None:
        order.is_hidden_from_livreurs = update_data.is_hidden_from_livreurs

    # Handle livreur assignment
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
        # Explicitly passed null → unassign
        order.assigned_livreur_id = None

    db.commit()
    db.refresh(order)
    return order


# ── Livreur-specific update endpoint ─────────────────────────────────────────


@router.patch("/{order_id}/livreur", response_model=EcommerceOrderResponse)
def livreur_update_order(
    order_id: int,
    update_data: EcommerceOrderLivreurUpdate,
    current_user: StoreUser = Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """
    Livreur updates their own fields on a visible order.
    Admins can also call this endpoint.
    Fields allowed: calling_status, delivery_status, livreur_notes.
    """
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
    hide: bool = Query(
        ..., description="true = hide from livreurs, false = make visible"
    ),
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    """
    Show or hide an order from all livreurs.
    Admin only.
    """
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
    livreur_id: Optional[int] = Query(
        None, description="Livreur ID, or omit to unassign"
    ),
    _admin: StoreUser = Depends(get_current_store_admin),
    db: Session = Depends(get_db),
):
    """
    Assign (or unassign) a livreur to an order.
    Admin only.
    Pass livreur_id=<id> to assign, omit or pass null to unassign.
    """
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
    """
    Permanently delete an order.
    Admin only — livreurs do NOT have access to this endpoint.
    """
    order = _get_order_or_404(order_id, db)
    db.delete(order)
    db.commit()
    return None
