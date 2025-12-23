
# server\routers\__init__.py
from .admin import router as admin_router
from .client import router as client_router
from .category import router as category_router
from .product import router as product_router
from .bill import router as bill_router
from .payment import router as payment_router
from .stock_alert import router as stock_alert_router
from .notification import router as notification_router
from .auth import router as auth_router
from .otp import router as otp_rout
from .upload import router as upload_images
from .client_account import router as client_account_router

__all__ = [
    "admin_router",
    "client_router",
    "category_router", 
    "product_router",
    "bill_router",
    "payment_router",
    "stock_alert_router",
    "notification_router",
    "auth_router",
    "otp_rout",
    "upload_images",
    "client_account_router"

]
