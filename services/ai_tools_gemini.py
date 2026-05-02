# services/ai_tools_gemini.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, extract
from datetime import datetime, timedelta
from models import (
    Bill, Product, Payment, ClientAccount,
    BillItem, Category, Client, StockAlert, Notification
)


# ══════════════════════════════════════════════════════════════
#  DASHBOARD & OVERVIEW
# ══════════════════════════════════════════════════════════════

def get_dashboard_stats(db: Session) -> dict:
    """Overall business stats: revenue, bills, clients, stock"""
    total_bills = db.query(func.count(Bill.id)).scalar() or 0
    paid_bills = db.query(func.count(Bill.id)).filter(
        Bill.status == "paid").scalar() or 0
    unpaid_bills = db.query(func.count(Bill.id)).filter(
        Bill.status == "not paid").scalar() or 0
    total_revenue = db.query(func.sum(Payment.amount_paid)).scalar() or 0
    total_remaining = db.query(func.sum(Bill.total_remaining)).scalar() or 0
    total_clients = db.query(func.count(Client.id)).filter(
        Client.is_active == True).scalar() or 0
    low_stock = db.query(func.count(Product.id)).filter(
        Product.quantity_in_stock <= Product.minimum_stock_level,
        Product.is_active == True
    ).scalar() or 0
    out_of_stock = db.query(func.count(Product.id)).filter(
        Product.quantity_in_stock == 0,
        Product.is_active == True
    ).scalar() or 0
    total_products = db.query(func.count(Product.id)).filter(
        Product.is_active == True).scalar() or 0

    return {
        "total_bills": total_bills,
        "paid_bills": paid_bills,
        "unpaid_bills": unpaid_bills,
        "total_revenue_collected": float(total_revenue),
        "total_remaining_to_collect": float(total_remaining),
        "total_active_clients": total_clients,
        "total_active_products": total_products,
        "low_stock_products": low_stock,
        "out_of_stock_products": out_of_stock,
    }


# ══════════════════════════════════════════════════════════════
#  BILLS
# ══════════════════════════════════════════════════════════════

def get_all_bills_with_status(db: Session) -> dict:
    """Get all bills with payment status and client name"""
    bills = db.query(Bill).order_by(desc(Bill.created_at)).limit(50).all()
    return {
        "bills": [
            {
                "bill_number": b.bill_number,
                "client": b.client.username if b.client else "unknown",
                "total_amount": float(b.total_amount),
                "total_paid": float(b.total_paid),
                "total_remaining": float(b.total_remaining),
                "status": b.status,
                "delivery_status": b.delivery_status,
                "created_at": str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_unpaid_bills(db: Session) -> dict:
    """Get all unpaid bills with client info and remaining amount"""
    bills = db.query(Bill).filter(
        Bill.status == "not paid"
    ).order_by(desc(Bill.total_remaining)).all()
    return {
        "count": len(bills),
        "total_remaining": float(sum(b.total_remaining for b in bills)),
        "bills": [
            {
                "bill_number": b.bill_number,
                "client": b.client.username if b.client else "unknown",
                "client_phone": b.client.phone_number if b.client else None,
                "total_amount": float(b.total_amount),
                "total_remaining": float(b.total_remaining),
                "created_at": str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_bills_by_client_name(db: Session, client_name: str) -> dict:
    """Get all bills for a specific client by name"""
    client = db.query(Client).filter(
        Client.username.ilike(f"%{client_name}%")
    ).first()
    if not client:
        return {"error": f"Client '{client_name}' not found"}
    bills = db.query(Bill).filter(Bill.client_id == client.id).order_by(
        desc(Bill.created_at)).all()
    return {
        "client": client.username,
        "email": client.email,
        "phone": client.phone_number,
        "total_bills": len(bills),
        "bills": [
            {
                "bill_number": b.bill_number,
                "total_amount": float(b.total_amount),
                "total_paid": float(b.total_paid),
                "total_remaining": float(b.total_remaining),
                "status": b.status,
                "delivery_status": b.delivery_status,
                "created_at": str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_bills_today(db: Session) -> dict:
    """Get all bills created today"""
    today = datetime.now().date()
    bills = db.query(Bill).filter(
        func.date(Bill.created_at) == today
    ).all()
    total = sum(b.total_amount for b in bills)
    return {
        "date": str(today),
        "count": len(bills),
        "total_amount": float(total),
        "bills": [
            {
                "bill_number": b.bill_number,
                "client": b.client.username if b.client else "unknown",
                "total_amount": float(b.total_amount),
                "status": b.status,
            }
            for b in bills
        ]
    }


def get_bills_this_month(db: Session) -> dict:
    """Get bills summary for the current month"""
    now = datetime.now()
    bills = db.query(Bill).filter(
        extract('month', Bill.created_at) == now.month,
        extract('year', Bill.created_at) == now.year
    ).all()
    total_amount = sum(b.total_amount for b in bills)
    total_paid = sum(b.total_paid for b in bills)
    total_remaining = sum(b.total_remaining for b in bills)
    return {
        "month": now.strftime("%B %Y"),
        "total_bills": len(bills),
        "paid_bills": sum(1 for b in bills if b.status == "paid"),
        "unpaid_bills": sum(1 for b in bills if b.status == "not paid"),
        "total_amount": float(total_amount),
        "total_collected": float(total_paid),
        "total_remaining": float(total_remaining),
    }


def get_bill_details_by_number(db: Session, bill_number: str) -> dict:
    """Get full details of a specific bill including all items"""
    bill = db.query(Bill).filter(Bill.bill_number == bill_number).first()
    if not bill:
        return {"error": f"Bill '{bill_number}' not found"}
    return {
        "bill_number": bill.bill_number,
        "client": bill.client.username if bill.client else "unknown",
        "client_phone": bill.client.phone_number if bill.client else None,
        "status": bill.status,
        "delivery_status": bill.delivery_status,
        "total_amount": float(bill.total_amount),
        "total_paid": float(bill.total_paid),
        "total_remaining": float(bill.total_remaining),
        "created_at": str(bill.created_at)[:10],
        "items": [
            {
                "product": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal),
            }
            for item in bill.bill_items
        ],
        "payments": [
            {
                "amount": float(p.amount_paid),
                "method": p.payment_method,
                "date": str(p.payment_date)[:10],
            }
            for p in bill.payments
        ]
    }


def get_delivery_status_summary(db: Session) -> dict:
    """Get count of bills by delivery status"""
    statuses = ["delivered", "on_the_way", "not_delivered"]
    result = {}
    for s in statuses:
        count = db.query(func.count(Bill.id)).filter(
            Bill.delivery_status == s).scalar() or 0
        result[s] = count
    return {"delivery_summary": result}


# ══════════════════════════════════════════════════════════════
#  CLIENTS
# ══════════════════════════════════════════════════════════════

def get_all_clients_summary(db: Session) -> dict:
    """List all active clients with balances and contact info"""
    clients = db.query(Client).filter(Client.is_active == True).all()
    return {
        "total": len(clients),
        "clients": [
            {
                "id": c.id,
                "username": c.username,
                "email": c.email,
                "phone": c.phone_number,
                "city": c.city,
                "total_amount": float(c.account.total_amount) if c.account else 0,
                "total_paid": float(c.account.total_paid) if c.account else 0,
                "total_remaining": float(c.account.total_remaining) if c.account else 0,
                "total_credit": float(c.account.total_credit) if c.account else 0,
            }
            for c in clients
        ]
    }


def get_client_details(db: Session, client_name: str) -> dict:
    """Get full profile and account details of a specific client"""
    client = db.query(Client).filter(
        Client.username.ilike(f"%{client_name}%")
    ).first()
    if not client:
        return {"error": f"Client '{client_name}' not found"}
    total_bills = db.query(func.count(Bill.id)).filter(
        Bill.client_id == client.id).scalar() or 0
    unpaid = db.query(func.count(Bill.id)).filter(
        Bill.client_id == client.id, Bill.status == "not paid"
    ).scalar() or 0
    return {
        "id": client.id,
        "username": client.username,
        "email": client.email,
        "phone": client.phone_number,
        "address": client.address,
        "city": client.city,
        "is_active": client.is_active,
        "member_since": str(client.created_at)[:10],
        "total_bills": total_bills,
        "unpaid_bills": unpaid,
        "account": {
            "total_amount": float(client.account.total_amount) if client.account else 0,
            "total_paid": float(client.account.total_paid) if client.account else 0,
            "total_remaining": float(client.account.total_remaining) if client.account else 0,
            "total_credit": float(client.account.total_credit) if client.account else 0,
        }
    }


def get_top_clients_by_debt(db: Session) -> dict:
    """Get clients with the highest remaining balance (most debt)"""
    accounts = db.query(ClientAccount).filter(
        ClientAccount.total_remaining > 0
    ).order_by(desc(ClientAccount.total_remaining)).limit(10).all()
    return {
        "clients": [
            {
                "client": a.client.username if a.client else "unknown",
                "phone": a.client.phone_number if a.client else None,
                "total_remaining": float(a.total_remaining),
                "total_amount": float(a.total_amount),
                "total_paid": float(a.total_paid),
            }
            for a in accounts
        ]
    }


def get_top_clients_by_revenue(db: Session) -> dict:
    """Get clients who spent the most (top buyers)"""
    accounts = db.query(ClientAccount).order_by(
        desc(ClientAccount.total_amount)
    ).limit(10).all()
    return {
        "clients": [
            {
                "client": a.client.username if a.client else "unknown",
                "total_spent": float(a.total_amount),
                "total_paid": float(a.total_paid),
                "total_remaining": float(a.total_remaining),
            }
            for a in accounts
        ]
    }


# ══════════════════════════════════════════════════════════════
#  PRODUCTS & INVENTORY
# ══════════════════════════════════════════════════════════════

def get_low_stock_products(db: Session) -> dict:
    """Get all products at or below minimum stock level"""
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_in_stock <= Product.minimum_stock_level
    ).order_by(Product.quantity_in_stock).all()
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "stock": p.quantity_in_stock,
                "minimum": p.minimum_stock_level,
                "category": p.category.name if p.category else "unknown",
                "price": float(p.price),
            }
            for p in products
        ]
    }


def get_out_of_stock_products(db: Session) -> dict:
    """Get all products with zero stock"""
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_in_stock == 0
    ).all()
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category.name if p.category else "unknown",
                "price": float(p.price),
            }
            for p in products
        ]
    }


def search_any_product(db: Session, query: str) -> dict:
    """Search any product by name including inactive ones"""
    products = db.query(Product).filter(
        Product.name.ilike(f"%{query}%")
    ).limit(15).all()
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "stock": p.quantity_in_stock,
                "minimum_stock": p.minimum_stock_level,
                "category": p.category.name if p.category else "unknown",
                "is_active": p.is_active,
                "is_on_sale": p.is_sold,
            }
            for p in products
        ]
    }


def get_products_by_category(db: Session, category_name: str) -> dict:
    """Get all products in a specific category"""
    category = db.query(Category).filter(
        Category.name.ilike(f"%{category_name}%")
    ).first()
    if not category:
        return {"error": f"Category '{category_name}' not found"}
    products = db.query(Product).filter(
        Product.category_id == category.id,
        Product.is_active == True
    ).all()
    return {
        "category": category.name,
        "total_products": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "stock": p.quantity_in_stock,
            }
            for p in products
        ]
    }


def get_all_categories_summary(db: Session) -> dict:
    """Get all categories with product count per category"""
    categories = db.query(Category).all()
    return {
        "categories": [
            {
                "name": c.name,
                "description": c.description,
                "product_count": len([p for p in c.products if p.is_active]),
            }
            for c in categories
        ]
    }


def get_top_selling_products(db: Session) -> dict:
    """Get the most sold products by quantity ordered"""
    results = db.query(
        BillItem.product_name,
        BillItem.product_id,
        func.sum(BillItem.quantity).label("total_qty"),
        func.sum(BillItem.subtotal).label("total_revenue"),
    ).group_by(BillItem.product_name, BillItem.product_id).order_by(
        desc("total_qty")
    ).limit(10).all()
    return {
        "top_products": [
            {
                "product": r.product_name,
                "total_quantity_sold": int(r.total_qty),
                "total_revenue": float(r.total_revenue),
            }
            for r in results
        ]
    }


# ══════════════════════════════════════════════════════════════
#  PAYMENTS
# ══════════════════════════════════════════════════════════════

def get_recent_payments(db: Session) -> dict:
    """Get the 20 most recent payments"""
    payments = db.query(Payment).order_by(
        desc(Payment.payment_date)).limit(20).all()
    return {
        "payments": [
            {
                "id": p.id,
                "bill_number": p.bill.bill_number if p.bill else "unknown",
                "client": p.bill.client.username if p.bill and p.bill.client else "unknown",
                "amount": float(p.amount_paid),
                "method": p.payment_method,
                "notes": p.notes,
                "date": str(p.payment_date)[:10],
            }
            for p in payments
        ]
    }


def get_payments_this_month(db: Session) -> dict:
    """Get total payments collected this month"""
    now = datetime.now()
    payments = db.query(Payment).filter(
        extract('month', Payment.payment_date) == now.month,
        extract('year', Payment.payment_date) == now.year
    ).all()
    total = sum(p.amount_paid for p in payments)
    by_method: dict = {}
    for p in payments:
        m = p.payment_method or "unknown"
        by_method[m] = by_method.get(m, 0) + float(p.amount_paid)
    return {
        "month": now.strftime("%B %Y"),
        "total_collected": float(total),
        "payment_count": len(payments),
        "by_method": by_method,
    }


def get_payments_today(db: Session) -> dict:
    """Get all payments received today"""
    today = datetime.now().date()
    payments = db.query(Payment).filter(
        func.date(Payment.payment_date) == today
    ).all()
    total = sum(p.amount_paid for p in payments)
    return {
        "date": str(today),
        "total_collected": float(total),
        "payment_count": len(payments),
        "payments": [
            {
                "bill_number": p.bill.bill_number if p.bill else "unknown",
                "client": p.bill.client.username if p.bill and p.bill.client else "unknown",
                "amount": float(p.amount_paid),
                "method": p.payment_method,
            }
            for p in payments
        ]
    }


# ══════════════════════════════════════════════════════════════
#  STOCK ALERTS
# ══════════════════════════════════════════════════════════════

def get_unresolved_stock_alerts(db: Session) -> dict:
    """Get all unresolved stock alerts"""
    alerts = db.query(StockAlert).filter(
        StockAlert.is_resolved == False
    ).order_by(desc(StockAlert.created_at)).all()
    return {
        "count": len(alerts),
        "alerts": [
            {
                "product": a.product.name if a.product else "unknown",
                "stock": a.product.quantity_in_stock if a.product else 0,
                "alert_type": a.alert_type,
                "message": a.message,
                "created_at": str(a.created_at)[:10],
            }
            for a in alerts
        ]
    }


# ══════════════════════════════════════════════════════════════
#  CLIENT TOOLS (limited access)
# ══════════════════════════════════════════════════════════════

def get_client_bills(db: Session, client_id: int) -> dict:
    """Get all bills for this specific client"""
    bills = db.query(Bill).filter(
        Bill.client_id == client_id
    ).order_by(desc(Bill.created_at)).limit(20).all()
    return {
        "total": len(bills),
        "bills": [
            {
                "bill_number": b.bill_number,
                "total_amount": float(b.total_amount),
                "total_paid": float(b.total_paid),
                "total_remaining": float(b.total_remaining),
                "status": b.status,
                "delivery_status": b.delivery_status,
                "created_at": str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_client_account_summary(db: Session, client_id: int) -> dict:
    """Get financial account summary for the client"""
    account = db.query(ClientAccount).filter(
        ClientAccount.client_id == client_id
    ).first()
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
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.name.ilike(f"%{query}%")
    ).limit(8).all()
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "in_stock": p.quantity_in_stock > 0,
                "on_sale": p.is_sold,
                "deep_link": f"myapp://product/{p.id}",
            }
            for p in products
        ]
    }


def get_bill_details_for_client(db: Session, client_id: int, bill_number: str) -> dict:
    """Get details of a specific bill belonging to this client"""
    bill = db.query(Bill).filter(
        Bill.client_id == client_id,
        Bill.bill_number == bill_number
    ).first()
    if not bill:
        return {"error": "Bill not found"}
    return {
        "bill_number": bill.bill_number,
        "status": bill.status,
        "delivery_status": bill.delivery_status,
        "total_amount": float(bill.total_amount),
        "total_paid": float(bill.total_paid),
        "total_remaining": float(bill.total_remaining),
        "created_at": str(bill.created_at)[:10],
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal),
                "deep_link": f"myapp://product/{item.product_id}" if item.product_id else None,
            }
            for item in bill.bill_items
        ]
    }


def get_client_unpaid_bills(db: Session, client_id: int) -> dict:
    """Get only unpaid bills for this client"""
    bills = db.query(Bill).filter(
        Bill.client_id == client_id,
        Bill.status == "not paid"
    ).all()
    total_remaining = sum(b.total_remaining for b in bills)
    return {
        "unpaid_count": len(bills),
        "total_remaining": float(total_remaining),
        "bills": [
            {
                "bill_number": b.bill_number,
                "total_amount": float(b.total_amount),
                "total_remaining": float(b.total_remaining),
                "created_at": str(b.created_at)[:10],
            }
            for b in bills
        ]
    }
