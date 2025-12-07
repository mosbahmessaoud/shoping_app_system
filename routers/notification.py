from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from models.notification import Notification
from schemas.notification import NotificationCreate, NotificationResponse, NotificationSummary
from utils.db import get_db
from utils.auth import get_current_admin, get_current_user

router = APIRouter(prefix="/notification", tags=["Notification"])


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create a new notification (accessible by clients and admins)"""

    # Handle both dict and object responses from get_current_user
    user_id = current_user.get('id') if isinstance(
        current_user, dict) else current_user.id
    is_client = current_user.get('username') if isinstance(
        current_user, dict) else hasattr(current_user, 'username')

    # If client is creating the notification, auto-set client_id
    if is_client and not (current_user.get('email') if isinstance(current_user, dict) else hasattr(current_user, 'email')):
        new_notification = Notification(
            notification_type=notification_data.notification_type,
            channel=notification_data.channel,
            message=notification_data.message,
            client_id=user_id,
            bill_id=notification_data.bill_id,
            stock_alert_id=notification_data.stock_alert_id,
            admin_id=notification_data.admin_id,
            is_sent=False
        )
    else:
        # Admin is creating the notification
        new_notification = Notification(
            notification_type=notification_data.notification_type,
            channel=notification_data.channel,
            message=notification_data.message,
            admin_id=notification_data.admin_id,
            client_id=notification_data.client_id,
            bill_id=notification_data.bill_id,
            stock_alert_id=notification_data.stock_alert_id,
            is_sent=False
        )

    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)

    return new_notification


@router.get("/", response_model=List[NotificationResponse])
def get_all_notifications(
    skip: int = 0,
    limit: int = 100,
    is_sent: bool = None,
    notification_type: str = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all notifications for the current client"""

    # FIX: Handle both dict and object responses
    user_id = current_user.get('id') if isinstance(
        current_user, dict) else current_user.id

    query = db.query(Notification).filter(
        Notification.client_id == user_id
    )

    if is_sent is not None:
        query = query.filter(Notification.is_sent == is_sent)

    if notification_type:
        query = query.filter(
            Notification.notification_type == notification_type,
        )

    notifications = query.order_by(
        Notification.created_at.desc()).offset(skip).limit(limit).all()

    return notifications


@router.get("/admin", response_model=List[NotificationResponse])
def get_admin_notifications(
    skip: int = 0,
    limit: int = 100,
    is_sent: bool = None,
    notification_type: str = None,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all notifications for admin"""

    # Handle both dict and object responses
    admin_id = current_admin.get('id') if isinstance(
        current_admin, dict) else current_admin.id

    query = db.query(Notification).filter(
        Notification.admin_id == admin_id
    )

    if is_sent is not None:
        query = query.filter(Notification.is_sent == is_sent)

    if notification_type:
        query = query.filter(
            Notification.notification_type == notification_type,
        )

    notifications = query.order_by(
        Notification.created_at.desc()).offset(skip).limit(limit).all()

    return notifications


@router.get("/pending", response_model=List[NotificationResponse])
def get_pending_notifications(
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get pending notifications (admin only)"""

    notifications = db.query(Notification).filter(
        Notification.is_sent == False
    ).order_by(Notification.created_at.desc()).all()

    return notifications


@router.get("/summary", response_model=NotificationSummary)
def get_notification_summary(
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get notification summary (admin only)"""

    total_notifications = db.query(Notification).count()
    sent_notifications = db.query(Notification).filter(
        Notification.is_sent == True).count()
    pending_notifications = db.query(Notification).filter(
        Notification.is_sent == False).count()
    email_notifications = db.query(Notification).filter(
        Notification.channel == "email").count()
    whatsapp_notifications = db.query(Notification).filter(
        Notification.channel == "whatsapp").count()

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
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get notification by ID (admin only)"""

    notification = db.query(Notification).filter(
        Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )

    return notification


@router.patch("/{notification_id}/mark-asread", response_model=NotificationResponse)
def mark_notification_sent(
    notification_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read """

    from datetime import datetime

    notification = db.query(Notification).filter(
        Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )

    if notification.is_sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette notification a déjà lire"
        )

    notification.is_sent = True
    notification.sent_at = datetime.now()

    db.commit()
    db.refresh(notification)

    return notification


@router.patch("/{notification_id}/mark-sent", response_model=NotificationResponse)
def mark_notification_sent(
    notification_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mark notification as sent (admin only)"""

    from datetime import datetime

    notification = db.query(Notification).filter(
        Notification.id == notification_id).first()
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


@router.patch("/{notification_id}/mark-sent", response_model=NotificationResponse)
def mark_notification_sent(
    notification_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mark notification as sent (admin only)"""

    from datetime import datetime

    notification = db.query(Notification).filter(
        Notification.id == notification_id).first()
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
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete notification (admin only)"""

    notification = db.query(Notification).filter(
        Notification.id == notification_id).first()
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
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Send all pending notifications (admin only)"""

    from datetime import datetime

    pending_notifications = db.query(Notification).filter(
        Notification.is_sent == False
    ).all()

    sent_count = 0
    for notification in pending_notifications:
        # TODO: Implement actual sending logic (email/WhatsApp)
        notification.is_sent = True
        notification.sent_at = datetime.now()
        sent_count += 1

    db.commit()

    return {
        "message": f"{sent_count} notification(s) envoyée(s) avec succès",
        "count": sent_count
    }
