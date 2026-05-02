# services/ai_tools.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import Bill, Product, Payment, ClientAccount, BillItem, Category, Client
import json


# ─────────────────────────────────────────────
#  CLIENT TOOLS  (limited access)
# ─────────────────────────────────────────────

def get_client_bills(db: Session, client_id: int) -> dict:
    """Get all bills for this specific client only"""
    bills = (
        db.query(Bill)
        .filter(Bill.client_id == client_id)
        .order_by(desc(Bill.created_at))
        .limit(10)
        .all()
    )
    return {
        "bills": [
            {
                "bill_number": b.bill_number,
                "total_amount": float(b.total_amount),
                "total_paid": float(b.total_paid),
                "total_remaining": float(b.total_remaining),
                "status": b.status,
                "delivery_status": b.delivery_status,
                "created_at": str(b.created_at),
            }
            for b in bills
        ]
    }


def get_client_account_summary(db: Session, client_id: int) -> dict:
    """Get the financial summary for this client"""
    account = db.query(ClientAccount).filter(
        ClientAccount.client_id == client_id).first()
    if not account:
        return {"error": "No account found"}
    return {
        "total_amount": float(account.total_amount),
        "total_paid": float(account.total_paid),
        "total_remaining": float(account.total_remaining),
        "total_credit": float(account.total_credit),
    }


def search_products_for_client(db: Session, query: str) -> dict:
    """Search active products visible to clients"""
    products = (
        db.query(Product)
        .filter(Product.is_active == True, Product.name.ilike(f"%{query}%"))
        .limit(5)
        .all()
    )
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "in_stock": p.quantity_in_stock > 0,
                "deep_link": f"myapp://product/{p.id}",
            }
            for p in products
        ]
    }


def get_bill_details_for_client(db: Session, client_id: int, bill_number: str) -> dict:
    """Get details of a specific bill (only if it belongs to this client)"""
    bill = db.query(Bill).filter(
        Bill.client_id == client_id,
        Bill.bill_number == bill_number
    ).first()
    if not bill:
        return {"error": "Bill not found"}
    items = [
        {
            "product_name": item.product_name,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "subtotal": float(item.subtotal),
            "product_id": item.product_id,
            "deep_link": f"myapp://product/{item.product_id}" if item.product_id else None,
        }
        for item in bill.bill_items
    ]
    return {
        "bill_number": bill.bill_number,
        "status": bill.status,
        "delivery_status": bill.delivery_status,
        "items": items,
        "total_amount": float(bill.total_amount),
        "total_remaining": float(bill.total_remaining),
    }


# ─────────────────────────────────────────────
#  ADMIN TOOLS  (full access)
# ─────────────────────────────────────────────

def get_dashboard_stats(db: Session) -> dict:
    """Overall business stats for admin"""
    total_bills = db.query(func.count(Bill.id)).scalar()
    unpaid_bills = db.query(func.count(Bill.id)).filter(
        Bill.status == "not paid").scalar()
    total_revenue = db.query(func.sum(Payment.amount_paid)).scalar() or 0
    low_stock = db.query(func.count(Product.id)).filter(
        Product.quantity_in_stock <= Product.minimum_stock_level
    ).scalar()
    total_clients = db.query(func.count(Client.id)).filter(
        Client.is_active == True).scalar()
    return {
        "total_bills": total_bills,
        "unpaid_bills": unpaid_bills,
        "total_revenue": float(total_revenue),
        "low_stock_products": low_stock,
        "total_active_clients": total_clients,
    }


def get_all_clients_summary(db: Session) -> dict:
    """List clients with their balances"""
    clients = db.query(Client).filter(Client.is_active == True).limit(20).all()
    return {
        "clients": [
            {
                "id": c.id,
                "username": c.username,
                "email": c.email,
                "total_remaining": float(c.account.total_remaining) if c.account else 0,
            }
            for c in clients
        ]
    }


def get_low_stock_products(db: Session) -> dict:
    """Get products at or below minimum stock level"""
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_in_stock <= Product.minimum_stock_level
    ).all()
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "stock": p.quantity_in_stock,
                "minimum": p.minimum_stock_level,
            }
            for p in products
        ]
    }


def search_any_product(db: Session, query: str) -> dict:
    """Search all products including inactive ones"""
    products = db.query(Product).filter(
        Product.name.ilike(f"%{query}%")).limit(10).all()
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "stock": p.quantity_in_stock,
                "is_active": p.is_active,
            }
            for p in products
        ]
    }


def get_recent_payments(db: Session, limit: int = 10) -> dict:
    """Get most recent payments"""
    payments = db.query(Payment).order_by(
        desc(Payment.payment_date)).limit(limit).all()
    return {
        "payments": [
            {
                "id": p.id,
                "bill_id": p.bill_id,
                "amount": float(p.amount_paid),
                "method": p.payment_method,
                "date": str(p.payment_date),
            }
            for p in payments
        ]
    }
