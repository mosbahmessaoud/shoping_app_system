from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Notification Base Schema
class NotificationBase(BaseModel):
    notification_type: str = Field(..., max_length=50)  # "new_bill", "stock_alert", "payment_received"
    channel: str = Field(..., max_length=20)  # "email" or "whatsapp"
    message: str = Field(..., max_length=1000)

# Notification Create Schema
class NotificationCreate(NotificationBase):
    admin_id: Optional[int] = None
    client_id: Optional[int] = None
    bill_id: Optional[int] = None
    stock_alert_id: Optional[int] = None

# Notification Update Schema
class NotificationUpdate(BaseModel):
    is_sent: bool
    sent_at: Optional[datetime] = None

# Notification Response Schema
class NotificationResponse(NotificationBase):
    id: int
    admin_id: Optional[int]
    client_id: Optional[int]
    bill_id: Optional[int]
    stock_alert_id: Optional[int]
    is_sent: bool
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

# Notification with Details
class NotificationWithDetails(NotificationResponse):
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None

    class Config:
        from_attributes = True

# Notification Summary
class NotificationSummary(BaseModel):
    total_notifications: int
    sent_notifications: int
    pending_notifications: int
    email_notifications: int
    whatsapp_notifications: int

    class Config:
        from_attributes = True