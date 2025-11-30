from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from models.notification import Notification
from schemas.notification import NotificationResponse, NotificationSummary
from utils.db import get_db
from utils.auth import get_current_admin

router = APIRouter(prefix="/notification", tags=["Notification"])

@router.get("/", response_model=List[NotificationResponse])
def get_all_notifications(
    skip: int = 0,
    limit: int = 100,
    is_sent: bool = None,
    notification_type: str = None,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir toutes les notifications (admin seulement)"""
    
    query = db.query(Notification)
    
    if is_sent is not None:
        query = query.filter(Notification.is_sent == is_sent)
    
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return notifications

@router.get("/pending", response_model=List[NotificationResponse])
def get_pending_notifications(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir les notifications en attente d'envoi (admin seulement)"""
    
    notifications = db.query(Notification).filter(
        Notification.is_sent == False
    ).order_by(Notification.created_at.desc()).all()
    
    return notifications

@router.get("/summary", response_model=NotificationSummary)
def get_notification_summary(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir le résumé des notifications (admin seulement)"""
    
    total_notifications = db.query(Notification).count()
    sent_notifications = db.query(Notification).filter(Notification.is_sent == True).count()
    pending_notifications = db.query(Notification).filter(Notification.is_sent == False).count()
    email_notifications = db.query(Notification).filter(Notification.channel == "email").count()
    whatsapp_notifications = db.query(Notification).filter(Notification.channel == "whatsapp").count()
    
    return NotificationSummary(
        total_notifications=total_notifications,
        sent_notifications=sent_notifications,
        pending_notifications=pending_notifications,
        email_notifications=email_notifications,
        whatsapp_notifications=whatsapp_notifications
    )

@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification_by_id(
    notification_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir une notification par son ID (admin seulement)"""
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    return notification

@router.patch("/{notification_id}/mark-sent", response_model=NotificationResponse)
def mark_notification_sent(
    notification_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Marquer une notification comme envoyée (admin seulement)"""
    
    from datetime import datetime
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    if notification.is_sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette notification a déjà été envoyée"
        )
    
    notification.is_sent = True
    notification.sent_at = datetime.now()
    
    db.commit()
    db.refresh(notification)
    
    return notification

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Supprimer une notification (admin seulement)"""
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    db.delete(notification)
    db.commit()
    
    return None

@router.post("/send-pending", response_model=dict)
def send_pending_notifications(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Envoyer toutes les notifications en attente (admin seulement)"""
    
    from datetime import datetime
    
    pending_notifications = db.query(Notification).filter(
        Notification.is_sent == False
    ).all()
    
    sent_count = 0
    for notification in pending_notifications:
        # Ici, vous devrez implémenter la logique d'envoi réel (email/WhatsApp)
        # Pour l'instant, nous marquons simplement comme envoyé
        notification.is_sent = True
        notification.sent_at = datetime.now()
        sent_count += 1
    
    db.commit()
    
    return {
        "message": f"{sent_count} notification(s) envoyée(s) avec succès",
        "count": sent_count
    }