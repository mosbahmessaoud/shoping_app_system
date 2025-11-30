"""
Models package initialization
Imports all models and database components for easy access
"""

# Import database components from utils.db
from utils.db import Base, engine, SessionLocal, get_db

# Import all models
from models.admin import Admin
from models.client import Client
from models.category import Category
from models.product import Product
from models.bill import Bill
from models.bill_item import BillItem
from models.payment import Payment
from models.stock_alert import StockAlert
from models.notification import Notification

# Define what's exported when using "from models import *"
__all__ = [
    # Database components
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    
    # Models
    "Admin",
    "Client",
    "Category",
    "Product",
    "Bill",
    "BillItem",
    "Payment",
    "StockAlert",
    "Notification",
]