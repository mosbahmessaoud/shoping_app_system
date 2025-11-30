from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
from models.stock_alert import StockAlert
from models.product import Product
from schemas.stock_alert import StockAlertResponse, StockAlertWithProduct, StockAlertUpdate, StockAlertSummary
from utils.db import get_db
from utils.auth import get_current_admin

router = APIRouter(prefix="/stock-alert", tags=["Stock Alert"])

@router.get("/", response_model=List[StockAlertWithProduct])
def get_all_stock_alerts(
    skip: int = 0,
    limit: int = 100,
    is_resolved: bool = None,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir toutes les alertes de stock (admin seulement)"""
    
    query = db.query(StockAlert).join(Product)
    
    if is_resolved is not None:
        query = query.filter(StockAlert.is_resolved == is_resolved)
    
    alerts = query.order_by(StockAlert.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for alert in alerts:
        product = alert.product
        result.append(StockAlertWithProduct(
            id=alert.id,
            product_id=alert.product_id,
            alert_type=alert.alert_type,
            message=alert.message,
            is_resolved=alert.is_resolved,
            created_at=alert.created_at,
            resolved_at=alert.resolved_at,
            product_name=product.name,
            quantity_in_stock=product.quantity_in_stock,
            minimum_stock_level=product.minimum_stock_level,
            category_name=product.category.name
        ))
    
    return result

@router.get("/unresolved", response_model=List[StockAlertWithProduct])
def get_unresolved_stock_alerts(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir les alertes de stock non résolues (admin seulement)"""
    
    alerts = db.query(StockAlert).join(Product).filter(
        StockAlert.is_resolved == False
    ).order_by(StockAlert.created_at.desc()).all()
    
    result = []
    for alert in alerts:
        product = alert.product
        result.append(StockAlertWithProduct(
            id=alert.id,
            product_id=alert.product_id,
            alert_type=alert.alert_type,
            message=alert.message,
            is_resolved=alert.is_resolved,
            created_at=alert.created_at,
            resolved_at=alert.resolved_at,
            product_name=product.name,
            quantity_in_stock=product.quantity_in_stock,
            minimum_stock_level=product.minimum_stock_level,
            category_name=product.category.name
        ))
    
    return result

@router.get("/summary", response_model=StockAlertSummary)
def get_stock_alert_summary(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir le résumé des alertes de stock (admin seulement)"""
    
    total_alerts = db.query(StockAlert).count()
    unresolved_alerts = db.query(StockAlert).filter(StockAlert.is_resolved == False).count()
    resolved_alerts = db.query(StockAlert).filter(StockAlert.is_resolved == True).count()
    critical_products = db.query(Product).filter(Product.quantity_in_stock == 0).count()
    
    return StockAlertSummary(
        total_alerts=total_alerts,
        unresolved_alerts=unresolved_alerts,
        resolved_alerts=resolved_alerts,
        critical_products=critical_products
    )

@router.get("/{alert_id}", response_model=StockAlertWithProduct)
def get_stock_alert_by_id(
    alert_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir une alerte de stock par son ID (admin seulement)"""
    
    alert = db.query(StockAlert).filter(StockAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte de stock non trouvée"
        )
    
    product = alert.product
    
    return StockAlertWithProduct(
        id=alert.id,
        product_id=alert.product_id,
        alert_type=alert.alert_type,
        message=alert.message,
        is_resolved=alert.is_resolved,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
        product_name=product.name,
        quantity_in_stock=product.quantity_in_stock,
        minimum_stock_level=product.minimum_stock_level,
        category_name=product.category.name
    )

@router.patch("/{alert_id}/resolve", response_model=StockAlertResponse)
def resolve_stock_alert(
    alert_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Résoudre une alerte de stock (admin seulement)"""
    
    alert = db.query(StockAlert).filter(StockAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte de stock non trouvée"
        )
    
    if alert.is_resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette alerte est déjà résolue"
        )
    
    alert.is_resolved = True
    alert.resolved_at = datetime.now()
    
    db.commit()
    db.refresh(alert)
    
    return alert

@router.patch("/{alert_id}/unresolve", response_model=StockAlertResponse)
def unresolve_stock_alert(
    alert_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Marquer une alerte comme non résolue (admin seulement)"""
    
    alert = db.query(StockAlert).filter(StockAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte de stock non trouvée"
        )
    
    alert.is_resolved = False
    alert.resolved_at = None
    
    db.commit()
    db.refresh(alert)
    
    return alert

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stock_alert(
    alert_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Supprimer une alerte de stock (admin seulement)"""
    
    alert = db.query(StockAlert).filter(StockAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte de stock non trouvée"
        )
    
    db.delete(alert)
    db.commit()
    
    return None