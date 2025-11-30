# Import all schemas for easy access
from .admin import (
    AdminBase,
    AdminCreate,
    AdminUpdate,
    AdminLogin,
    AdminResponse,
    AdminWithToken
)

from .client import (
    ClientBase,
    ClientCreate,
    ClientUpdate,
    ClientLogin,
    ClientResponse,
    ClientWithToken,
    ClientSummary
)

from .category import (
    CategoryBase,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithCount
)

from .product import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductWithCategory,
    ProductStockStatus
)

from .bill import (
    BillItemCreate,
    BillItemResponse,
    BillCreate,
    BillBase,
    BillResponse,
    BillWithItems,
    BillWithClient,
    BillSummary
)

from .payment import (
    PaymentBase,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentWithBillInfo,
    PaymentHistory
)

from .stock_alert import (
    StockAlertBase,
    StockAlertCreate,
    StockAlertUpdate,
    StockAlertResponse,
    StockAlertWithProduct,
    StockAlertSummary
)

from .notification import (
    NotificationBase,
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationWithDetails,
    NotificationSummary
)

__all__ = [
    # Admin schemas
    "AdminBase", "AdminCreate", "AdminUpdate", "AdminLogin", 
    "AdminResponse", "AdminWithToken",
    
    # Client schemas
    "ClientBase", "ClientCreate", "ClientUpdate", "ClientLogin", 
    "ClientResponse", "ClientWithToken", "ClientSummary",
    
    # Category schemas
    "CategoryBase", "CategoryCreate", "CategoryUpdate", 
    "CategoryResponse", "CategoryWithCount",
    
    # Product schemas
    "ProductBase", "ProductCreate", "ProductUpdate", 
    "ProductResponse", "ProductWithCategory", "ProductStockStatus",
    
    # Bill schemas
    "BillItemCreate", "BillItemResponse", "BillCreate", "BillBase",
    "BillResponse", "BillWithItems", "BillWithClient", "BillSummary",
    
    # Payment schemas
    "PaymentBase", "PaymentCreate", "PaymentUpdate", 
    "PaymentResponse", "PaymentWithBillInfo", "PaymentHistory",
    
    # Stock Alert schemas
    "StockAlertBase", "StockAlertCreate", "StockAlertUpdate", 
    "StockAlertResponse", "StockAlertWithProduct", "StockAlertSummary",
    
    # Notification schemas
    "NotificationBase", "NotificationCreate", "NotificationUpdate", 
    "NotificationResponse", "NotificationWithDetails", "NotificationSummary"
]