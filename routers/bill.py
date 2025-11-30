from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from models.bill import Bill
from models.bill_item import BillItem
from models.product import Product
from models.client import Client
from schemas.bill import BillCreate, BillResponse, BillWithItems, BillWithClient, BillSummary
from utils.db import get_db
from utils.auth import get_current_client, get_current_admin
from utils.stock_manager import check_and_create_stock_alert
from utils.notification_manager import create_bill_notification
from sqlalchemy import func, extract, and_, cast, Date

router = APIRouter(prefix="/bill", tags=["Bill"])


@router.get("/statistics/daily", response_model=List[dict])
def get_daily_bill_summary(
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., description="Month (1-12)"),
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get daily bill summary for a specific month"""

    # Query bills for the specific month and group by day
    results = db.query(
        func.to_char(Bill.created_at, 'YYYY-MM-DD').label("date"),
        func.count(Bill.id).label("total_bills"),
        func.sum(Bill.total_amount).label("total_revenue"),
        func.sum(Bill.total_paid).label("total_paid"),
        func.sum(Bill.total_remaining).label("total_pending"),
        func.count(func.nullif(Bill.status == 'paid', False)
                   ).label("paid_bills"),
        func.count(func.nullif(Bill.status == 'not paid', False)
                   ).label("unpaid_bills")
    ).filter(
        and_(
            extract('year', Bill.created_at) == year,
            extract('month', Bill.created_at) == month
        )
    ).group_by("date").order_by("date").all()

    daily_summary = []
    for row in results:
        daily_summary.append({
            "period": row.date,
            "total_bills": row.total_bills or 0,
            "total_revenue": float(row.total_revenue or Decimal('0.00')),
            "total_paid": float(row.total_paid or Decimal('0.00')),
            "total_pending": float(row.total_pending or Decimal('0.00')),
            "paid_bills": row.paid_bills or 0,
            "unpaid_bills": row.unpaid_bills or 0
        })

    return daily_summary


@router.get("/statistics/monthly", response_model=List[dict])
def get_monthly_bill_summary(
    year: Optional[int] = Query(
        None, description="Year (e.g., 2024). If not provided, returns all months"),
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get monthly bill summary, optionally filtered by year"""

    query = db.query(
        func.to_char(Bill.created_at, 'YYYY-MM').label("month"),
        func.count(Bill.id).label("total_bills"),
        func.sum(Bill.total_amount).label("total_revenue"),
        func.sum(Bill.total_paid).label("total_paid"),
        func.sum(Bill.total_remaining).label("total_pending"),
        func.count(func.nullif(Bill.status == 'paid', False)
                   ).label("paid_bills"),
        func.count(func.nullif(Bill.status == 'not paid', False)
                   ).label("unpaid_bills")
    )

    if year:
        query = query.filter(extract('year', Bill.created_at) == year)

    results = query.group_by("month").order_by("month").all()

    monthly_summary = []
    for row in results:
        monthly_summary.append({
            "period": row.month,
            "total_bills": row.total_bills or 0,
            "total_revenue": float(row.total_revenue or Decimal('0.00')),
            "total_paid": float(row.total_paid or Decimal('0.00')),
            "total_pending": float(row.total_pending or Decimal('0.00')),
            "paid_bills": row.paid_bills or 0,
            "unpaid_bills": row.unpaid_bills or 0
        })

    return monthly_summary


@router.get("/statistics/yearly", response_model=List[dict])
def get_yearly_bill_summary(
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get yearly bill summary"""

    results = db.query(
        func.to_char(Bill.created_at, 'YYYY').label("year"),
        func.count(Bill.id).label("total_bills"),
        func.sum(Bill.total_amount).label("total_revenue"),
        func.sum(Bill.total_paid).label("total_paid"),
        func.sum(Bill.total_remaining).label("total_pending"),
        func.count(func.nullif(Bill.status == 'paid', False)
                   ).label("paid_bills"),
        func.count(func.nullif(Bill.status == 'not paid', False)
                   ).label("unpaid_bills")
    ).group_by("year").order_by("year").all()

    yearly_summary = []
    for row in results:
        yearly_summary.append({
            "period": row.year,
            "total_bills": row.total_bills or 0,
            "total_revenue": float(row.total_revenue or Decimal('0.00')),
            "total_paid": float(row.total_paid or Decimal('0.00')),
            "total_pending": float(row.total_pending or Decimal('0.00')),
            "paid_bills": row.paid_bills or 0,
            "unpaid_bills": row.unpaid_bills or 0
        })

    return yearly_summary


@router.get("/statistics/period-range", response_model=List[dict])
def get_period_range_summary(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    group_by: str = Query("day", description="Group by: day, month, or year"),
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get bill summary for a date range, grouped by specified period"""

    # Determine the grouping format
    format_map = {
        "day": "YYYY-MM-DD",
        "month": "YYYY-MM",
        "year": "YYYY"
    }

    if group_by not in format_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by must be 'day', 'month', or 'year'"
        )

    date_format = format_map[group_by]

    results = db.query(
        func.to_char(Bill.created_at, date_format).label("period"),
        func.count(Bill.id).label("total_bills"),
        func.sum(Bill.total_amount).label("total_revenue"),
        func.sum(Bill.total_paid).label("total_paid"),
        func.sum(Bill.total_remaining).label("total_pending"),
        func.count(func.nullif(Bill.status == 'paid', False)
                   ).label("paid_bills"),
        func.count(func.nullif(Bill.status == 'not paid', False)
                   ).label("unpaid_bills")
    ).filter(
        and_(
            cast(Bill.created_at, Date) >= start_date,
            cast(Bill.created_at, Date) <= end_date
        )
    ).group_by("period").order_by("period").all()

    summary = []
    for row in results:
        summary.append({
            "period": row.period,
            "total_bills": row.total_bills or 0,
            "total_revenue": float(row.total_revenue or Decimal('0.00')),
            "total_paid": float(row.total_paid or Decimal('0.00')),
            "total_pending": float(row.total_pending or Decimal('0.00')),
            "paid_bills": row.paid_bills or 0,
            "unpaid_bills": row.unpaid_bills or 0
        })

    return summary


@router.post("/", response_model=BillWithItems, status_code=status.HTTP_201_CREATED)
def create_bill(
    bill_data: BillCreate,
    current_client=Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle facture (client seulement)"""

    # Générer un numéro de facture unique
    bill_count = db.query(Bill).count()
    bill_number = f"BILL-{datetime.now().strftime('%Y%m%d')}-{bill_count + 1:04d}"

    # Créer la facture
    new_bill = Bill(
        client_id=current_client.id,
        bill_number=bill_number,
        total_amount=Decimal('0.00'),
        total_paid=Decimal('0.00'),
        total_remaining=Decimal('0.00'),
        status="not paid"
    )

    db.add(new_bill)
    db.flush()

    # Ajouter les articles de la facture
    total_amount = Decimal('0.00')
    bill_items = []

    for item in bill_data.items:
        # Vérifier si le produit existe
        product = db.query(Product).filter(
            Product.id == item.product_id).first()
        if not product:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produit avec ID {item.product_id} non trouvé"
            )

        # Vérifier si le produit est actif
        if not product.is_active:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le produit '{product.name}' n'est pas disponible"
            )

        # Vérifier le stock
        if product.quantity_in_stock < item.quantity:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuffisant pour le produit '{product.name}'. Stock disponible: {product.quantity_in_stock}"
            )

        # Calculer le sous-total
        subtotal = product.price * item.quantity
        total_amount += subtotal

        # Créer l'article de facture
        bill_item = BillItem(
            bill_id=new_bill.id,
            product_id=product.id,
            product_name=product.name,
            unit_price=product.price,
            quantity=item.quantity,
            subtotal=subtotal
        )
        db.add(bill_item)
        bill_items.append(bill_item)

        # Décrémenter le stock
        product.quantity_in_stock -= item.quantity

        # Vérifier et créer une alerte de stock si nécessaire
        check_and_create_stock_alert(db, product)

    # Mettre à jour les totaux de la facture
    new_bill.total_amount = total_amount
    new_bill.total_remaining = total_amount

    db.commit()
    db.refresh(new_bill)

    # Créer une notification pour l'admin
    create_bill_notification(db, new_bill, current_client)

    return BillWithItems(
        id=new_bill.id,
        bill_number=new_bill.bill_number,
        client_id=new_bill.client_id,
        total_amount=new_bill.total_amount,
        total_paid=new_bill.total_paid,
        total_remaining=new_bill.total_remaining,
        status=new_bill.status,
        created_at=new_bill.created_at,
        updated_at=new_bill.updated_at,
        notification_sent=new_bill.notification_sent,
        items=[{
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "subtotal": item.subtotal,
            "created_at": item.created_at
        } for item in bill_items]
    )


@router.get("/my-bills", response_model=List[BillWithItems])
def get_my_bills(
    skip: int = 0,
    limit: int = 100,
    current_client=Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """Obtenir toutes les factures du client connecté"""

    bills = db.query(Bill).filter(Bill.client_id ==
                                  current_client.id).offset(skip).limit(limit).all()

    result = []
    for bill in bills:
        result.append(BillWithItems(
            id=bill.id,
            bill_number=bill.bill_number,
            client_id=bill.client_id,
            total_amount=bill.total_amount,
            total_paid=bill.total_paid,
            total_remaining=bill.total_remaining,
            status=bill.status,
            created_at=bill.created_at,
            updated_at=bill.updated_at,
            notification_sent=bill.notification_sent,
            items=[{
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "unit_price": item.unit_price,
                "quantity": item.quantity,
                "subtotal": item.subtotal,
                "created_at": item.created_at
            } for item in bill.bill_items]
        ))

    return result

# count all my bills


@router.get("/my-bills/count")
def count_my_bills(
    current_client=Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """Obtenir le nombre total de factures du client connecté"""

    count = db.query(Bill).filter(Bill.client_id == current_client.id).count()

    return {"count": count}

# count all unpaid bills


@router.get("/unpaid-bills/count")
def count_my_bills(
    current_client=Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """Obtenir le nombre total de factures du client connecté"""

    count = db.query(Bill).filter(

        Bill.client_id == current_client.id,
        Bill.status == "not paid"
    ).count()

    return {"count_unpaid": count}


@router.get("/all", response_model=List[BillWithClient])
def get_all_bills(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir toutes les factures (admin seulement)"""

    query = db.query(Bill)

    if status_filter:
        query = query.filter(Bill.status == status_filter)

    bills = query.offset(skip).limit(limit).all()

    result = []
    for bill in bills:
        result.append(BillWithClient(
            id=bill.id,
            bill_number=bill.bill_number,
            client_id=bill.client_id,
            total_amount=bill.total_amount,
            total_paid=bill.total_paid,
            total_remaining=bill.total_remaining,
            status=bill.status,
            created_at=bill.created_at,
            updated_at=bill.updated_at,
            notification_sent=bill.notification_sent,
            client_name=bill.client.username,
            client_email=bill.client.email,
            client_phone=bill.client.phone_number,
            items=[{
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "unit_price": item.unit_price,
                "quantity": item.quantity,
                "subtotal": item.subtotal,
                "created_at": item.created_at
            } for item in bill.bill_items]
        ))

    return result


@router.get("/summary", response_model=BillSummary)
def get_bill_summary(
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir le résumé des factures (admin seulement)"""

    total_bills = db.query(Bill).count()
    total_revenue = db.query(func.sum(Bill.total_amount)
                             ).scalar() or Decimal('0.00')
    total_paid = db.query(func.sum(Bill.total_paid)
                          ).scalar() or Decimal('0.00')
    total_pending = db.query(
        func.sum(Bill.total_remaining)).scalar() or Decimal('0.00')
    paid_bills = db.query(Bill).filter(Bill.status == "paid").count()
    unpaid_bills = db.query(Bill).filter(Bill.status == "not paid").count()

    return BillSummary(
        total_bills=total_bills,
        total_revenue=total_revenue,
        total_paid=total_paid,
        total_pending=total_pending,
        paid_bills=paid_bills,
        unpaid_bills=unpaid_bills
    )

# summary monthly bills - Fixed for PostgreSQL


@router.get("/summary/monthly", response_model=List[BillSummary])
def get_monthly_bill_summary(
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir le résumé mensuel des factures (admin seulement)"""

    monthly_summary = []

    # PostgreSQL uses TO_CHAR instead of strftime
    results = db.query(
        func.to_char(Bill.created_at, 'YYYY-MM').label("month"),
        func.count(Bill.id).label("total_bills"),
        func.sum(Bill.total_amount).label("total_revenue"),
        func.sum(Bill.total_paid).label("total_paid"),
        func.sum(Bill.total_remaining).label("total_pending")
    ).group_by("month").order_by("month").all()

    for row in results:
        monthly_summary.append(BillSummary(
            total_bills=row.total_bills,
            total_revenue=row.total_revenue or Decimal('0.00'),
            total_paid=row.total_paid or Decimal('0.00'),
            total_pending=row.total_pending or Decimal('0.00'),
            paid_bills=0,  # Non calculé dans ce résumé
            unpaid_bills=0  # Non calculé dans ce résumé
        ))

    return monthly_summary


@router.get("/{bill_id}", response_model=BillWithItems)
def get_bill_by_id(
    bill_id: int,
    current_client=Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """Obtenir une facture par son ID"""

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture non trouvée"
        )

    # Vérifier que le client accède à sa propre facture
    if bill.client_id != current_client.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas accès à cette facture"
        )

    return BillWithItems(
        id=bill.id,
        bill_number=bill.bill_number,
        client_id=bill.client_id,
        total_amount=bill.total_amount,
        total_paid=bill.total_paid,
        total_remaining=bill.total_remaining,
        status=bill.status,
        created_at=bill.created_at,
        updated_at=bill.updated_at,
        notification_sent=bill.notification_sent,
        items=[{
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "subtotal": item.subtotal,
            "created_at": item.created_at
        } for item in bill.bill_items]
    )

# admin pay a bill


@router.post("/{bill_id}/pay", response_model=BillResponse)
def pay_bill(
    bill_id: int,
    amount: Decimal = Query(..., gt=0, description="Amount to pay"),
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Payer une facture (admin seulement)"""

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture non trouvée"
        )

    if bill.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La facture est déjà payée"
        )

    if amount > bill.total_remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le montant payé dépasse le montant restant"
        )

    # Mettre à jour les montants de la facture
    bill.total_paid += amount
    bill.total_remaining -= amount

    if bill.total_remaining == Decimal('0.00'):
        bill.status = "paid"

    db.commit()
    db.refresh(bill)

    return BillResponse(
        id=bill.id,
        bill_number=bill.bill_number,
        client_id=bill.client_id,
        total_amount=bill.total_amount,
        total_paid=bill.total_paid,
        total_remaining=bill.total_remaining,
        status=bill.status,
        created_at=bill.created_at,
        updated_at=bill.updated_at,
        notification_sent=bill.notification_sent
    )


@router.get("/admin/{bill_id}", response_model=BillWithClient)
def get_bill_by_id_admin(
    bill_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir une facture par son ID (admin seulement)"""

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture non trouvée"
        )

    return BillWithClient(
        id=bill.id,
        bill_number=bill.bill_number,
        client_id=bill.client_id,
        total_amount=bill.total_amount,
        total_paid=bill.total_paid,
        total_remaining=bill.total_remaining,
        status=bill.status,
        created_at=bill.created_at,
        updated_at=bill.updated_at,
        notification_sent=bill.notification_sent,
        client_name=bill.client.username,
        client_email=bill.client.email,
        client_phone=bill.client.phone_number,
        items=[{
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "subtotal": item.subtotal,
            "created_at": item.created_at
        } for item in bill.bill_items]
    )
