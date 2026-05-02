# services/ai_tools_groq.py
"""
All database query functions exposed as AI tools.

ADMIN tools  → full business access (revenue, clients, stock, payments, bills)
CLIENT tools → scoped to the authenticated client's own data only
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, extract, cast, Date
from datetime import datetime, timedelta
from models import (
    Bill, Product, Payment, ClientAccount,
    BillItem, Category, Client, StockAlert, Notification
)


# ══════════════════════════════════════════════════════════════
#  ADMIN — DASHBOARD & OVERVIEW
# ══════════════════════════════════════════════════════════════

def get_dashboard_stats(db: Session) -> dict:
    """
    Overall business snapshot:
    | Metric               | Value |
    |----------------------|-------|
    | Total bills          | ...   |
    | Paid / Unpaid        | ...   |
    | Revenue collected    | ...   |
    | Remaining to collect | ...   |
    | Active clients       | ...   |
    | Active products      | ...   |
    | Low-stock products   | ...   |
    | Out-of-stock         | ...   |
    """
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
#  ADMIN — BILLS
# ══════════════════════════════════════════════════════════════

def get_all_bills_with_status(db: Session) -> dict:
    """
    Last 50 bills with client name, amounts, payment status, and delivery status.
    Covers questions like:
    - "Show me all recent bills"
    - "What is the status of latest bills?"
    - "Which bills are paid / unpaid?"
    """
    bills = db.query(Bill).order_by(desc(Bill.created_at)).limit(50).all()
    return {
        "bills": [
            {
                "bill_number":      b.bill_number,
                "client":           b.client.username if b.client else "unknown",
                "total_amount":     float(b.total_amount),
                "total_paid":       float(b.total_paid),
                "total_remaining":  float(b.total_remaining),
                "status":           b.status,
                "delivery_status":  b.delivery_status,
                "created_at":       str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_unpaid_bills(db: Session) -> dict:
    """
    All unpaid bills sorted by highest remaining amount.
    Covers questions like:
    - "Which clients still owe money?"
    - "What are all unpaid invoices?"
    - "How much total is still uncollected?"
    """
    bills = db.query(Bill).filter(Bill.status == "not paid").order_by(
        desc(Bill.total_remaining)).all()
    return {
        "count": len(bills),
        "total_remaining": float(sum(b.total_remaining for b in bills)),
        "bills": [
            {
                "bill_number":     b.bill_number,
                "client":          b.client.username if b.client else "unknown",
                "client_phone":    b.client.phone_number if b.client else None,
                "total_amount":    float(b.total_amount),
                "total_remaining": float(b.total_remaining),
                "created_at":      str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_bills_today(db: Session) -> dict:
    """
    All bills created today with total count and amount.
    Covers questions like:
    - "How many bills did we make today?"
    - "What is today's sales total?"
    - "Show me today's orders"
    """
    today = datetime.now().date()
    bills = db.query(Bill).filter(func.date(Bill.created_at) == today).all()
    return {
        "date":         str(today),
        "count":        len(bills),
        "total_amount": float(sum(b.total_amount for b in bills)),
        "bills": [
            {
                "bill_number":  b.bill_number,
                "client":       b.client.username if b.client else "unknown",
                "total_amount": float(b.total_amount),
                "status":       b.status,
            }
            for b in bills
        ]
    }


def get_bills_this_month(db: Session) -> dict:
    """
    Bills summary for the current calendar month.
    Covers questions like:
    - "How is the store performing this month?"
    - "Monthly sales report"
    - "How much revenue this month?"
    - "How many unpaid bills this month?"
    """
    now = datetime.now()
    bills = db.query(Bill).filter(
        extract("month", Bill.created_at) == now.month,
        extract("year", Bill.created_at) == now.year,
    ).all()
    return {
        "month":           now.strftime("%B %Y"),
        "total_bills":     len(bills),
        "paid_bills":      sum(1 for b in bills if b.status == "paid"),
        "unpaid_bills":    sum(1 for b in bills if b.status == "not paid"),
        "total_amount":    float(sum(b.total_amount for b in bills)),
        "total_collected": float(sum(b.total_paid for b in bills)),
        "total_remaining": float(sum(b.total_remaining for b in bills)),
    }


def get_bills_last_7_days(db: Session) -> dict:
    """
    Bills created in the last 7 days, grouped by date.
    Covers questions like:
    - "Show me this week's activity"
    - "Sales trend last 7 days"
    - "Weekly overview"
    """
    since = datetime.now().date() - timedelta(days=6)
    bills = db.query(Bill).filter(
        func.date(Bill.created_at) >= since
    ).order_by(asc(Bill.created_at)).all()

    by_date: dict = {}
    for b in bills:
        d = str(b.created_at)[:10]
        if d not in by_date:
            by_date[d] = {"count": 0, "total_amount": 0.0}
        by_date[d]["count"] += 1
        by_date[d]["total_amount"] += float(b.total_amount)

    return {
        "period":    f"{since} → {datetime.now().date()}",
        "total_bills": len(bills),
        "by_date":   by_date,
    }


def get_bill_details_by_number(db: Session, bill_number: str) -> dict:
    """
    Full breakdown of a specific bill: items, amounts, and payment history.
    Args:
        bill_number: The bill number to look up (e.g. BILL-001).
    Covers questions like:
    - "Show me the details of bill BILL-042"
    - "What items are in invoice X?"
    - "Has bill X been paid?"
    """
    bill = db.query(Bill).filter(Bill.bill_number == bill_number).first()
    if not bill:
        return {"error": f"Bill '{bill_number}' not found"}
    return {
        "bill_number":     bill.bill_number,
        "client":          bill.client.username if bill.client else "unknown",
        "client_phone":    bill.client.phone_number if bill.client else None,
        "status":          bill.status,
        "delivery_status": bill.delivery_status,
        "total_amount":    float(bill.total_amount),
        "total_paid":      float(bill.total_paid),
        "total_remaining": float(bill.total_remaining),
        "created_at":      str(bill.created_at)[:10],
        "items": [
            {
                "product":    item.product_name,
                "quantity":   item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal":   float(item.subtotal),
            }
            for item in bill.bill_items
        ],
        "payments": [
            {
                "amount": float(p.amount_paid),
                "method": p.payment_method,
                "date":   str(p.payment_date)[:10],
            }
            for p in bill.payments
        ]
    }


def get_bills_by_client_name(db: Session, client_name: str) -> dict:
    """
    All bills belonging to a specific client by name.
    Args:
        client_name: Full or partial client name to search for.
    Covers questions like:
    - "Show all orders for client Ahmed"
    - "What bills does [name] have?"
    - "Check invoice history for [name]"
    """
    client = db.query(Client).filter(
        Client.username.ilike(f"%{client_name}%")).first()
    if not client:
        return {"error": f"Client '{client_name}' not found"}
    bills = db.query(Bill).filter(Bill.client_id == client.id).order_by(
        desc(Bill.created_at)).all()
    return {
        "client":      client.username,
        "phone":       client.phone_number,
        "total_bills": len(bills),
        "total_paid_overall":    float(client.account.total_paid) if client.account else 0,
        "total_remaining_overall": float(client.account.total_remaining) if client.account else 0,
        "bills": [
            {
                "bill_number":     b.bill_number,
                "total_amount":    float(b.total_amount),
                "total_paid":      float(b.total_paid),
                "total_remaining": float(b.total_remaining),
                "status":          b.status,
                "delivery_status": b.delivery_status,
                "created_at":      str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_delivery_status_summary(db: Session) -> dict:
    """
    Count of bills by delivery status: delivered / on_the_way / not_delivered.
    Covers questions like:
    - "How many orders are still pending delivery?"
    - "Delivery overview"
    - "Which orders are on the way?"
    """
    statuses = ["delivered", "on_the_way", "not_delivered"]
    result = {}
    for s in statuses:
        result[s] = db.query(func.count(Bill.id)).filter(
            Bill.delivery_status == s).scalar() or 0
    return {"delivery_summary": result}


def get_bills_not_delivered(db: Session) -> dict:
    """
    All bills that have not been delivered yet.
    Covers questions like:
    - "Which orders haven't been delivered?"
    - "Pending deliveries list"
    - "Orders still waiting to ship"
    """
    bills = db.query(Bill).filter(
        Bill.delivery_status == "not_delivered"
    ).order_by(desc(Bill.created_at)).all()
    return {
        "count": len(bills),
        "bills": [
            {
                "bill_number": b.bill_number,
                "client":      b.client.username if b.client else "unknown",
                "phone":       b.client.phone_number if b.client else None,
                "total_amount": float(b.total_amount),
                "status":      b.status,
                "created_at":  str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


# ══════════════════════════════════════════════════════════════
#  ADMIN — CLIENTS
# ══════════════════════════════════════════════════════════════

def get_all_clients_summary(db: Session) -> dict:
    """
    All active clients with contact info and account balances.
    Covers questions like:
    - "List all clients"
    - "Who are our customers?"
    - "Show clients with their balances"
    """
    clients = db.query(Client).filter(Client.is_active == True).all()
    return {
        "total": len(clients),
        "clients": [
            {
                "id":              c.id,
                "username":        c.username,
                "phone":           c.phone_number,
                "city":            c.city,
                "total_amount":    float(c.account.total_amount) if c.account else 0,
                "total_paid":      float(c.account.total_paid) if c.account else 0,
                "total_remaining": float(c.account.total_remaining) if c.account else 0,
                "total_credit":    float(c.account.total_credit) if c.account else 0,
            }
            for c in clients
        ]
    }


def get_client_details(db: Session, client_name: str) -> dict:
    """
    Full profile, address, account balances, and bill counts for one client.
    Args:
        client_name: Full or partial name of the client.
    Covers questions like:
    - "Tell me everything about client [name]"
    - "What is [name]'s current balance?"
    - "How many bills does [name] have?"
    - "Is [name] still active?"
    """
    client = db.query(Client).filter(
        Client.username.ilike(f"%{client_name}%")).first()
    if not client:
        return {"error": f"Client '{client_name}' not found"}
    total_bills = db.query(func.count(Bill.id)).filter(
        Bill.client_id == client.id).scalar() or 0
    unpaid = db.query(func.count(Bill.id)).filter(
        Bill.client_id == client.id, Bill.status == "not paid"
    ).scalar() or 0
    return {
        "id":           client.id,
        "username":     client.username,
        "email":        client.email,
        "phone":        client.phone_number,
        "address":      client.address,
        "city":         client.city,
        "is_active":    client.is_active,
        "member_since": str(client.created_at)[:10],
        "total_bills":  total_bills,
        "unpaid_bills": unpaid,
        "account": {
            "total_amount":    float(client.account.total_amount) if client.account else 0,
            "total_paid":      float(client.account.total_paid) if client.account else 0,
            "total_remaining": float(client.account.total_remaining) if client.account else 0,
            "total_credit":    float(client.account.total_credit) if client.account else 0,
        }
    }


def get_top_clients_by_debt(db: Session) -> dict:
    """
    Top 10 clients with the highest unpaid balance (most debt).
    Covers questions like:
    - "Who owes us the most money?"
    - "Clients with highest debt"
    - "Top debtors list"
    - "Which clients haven't fully paid?"
    """
    accounts = db.query(ClientAccount).filter(
        ClientAccount.total_remaining > 0
    ).order_by(desc(ClientAccount.total_remaining)).limit(10).all()
    return {
        "clients": [
            {
                "client":          a.client.username if a.client else "unknown",
                "phone":           a.client.phone_number if a.client else None,
                "city":            a.client.city if a.client else None,
                "total_remaining": float(a.total_remaining),
                "total_amount":    float(a.total_amount),
                "total_paid":      float(a.total_paid),
            }
            for a in accounts
        ]
    }


def get_top_clients_by_revenue(db: Session) -> dict:
    """
    Top 10 clients by total purchase amount (best buyers).
    Covers questions like:
    - "Who are our best clients?"
    - "Top buyers / VIP clients"
    - "Which clients spend the most?"
    - "Client revenue ranking"
    """
    accounts = db.query(ClientAccount).order_by(
        desc(ClientAccount.total_amount)).limit(10).all()
    return {
        "clients": [
            {
                "client":          a.client.username if a.client else "unknown",
                "total_spent":     float(a.total_amount),
                "total_paid":      float(a.total_paid),
                "total_remaining": float(a.total_remaining),
                "total_credit":    float(a.total_credit),
            }
            for a in accounts
        ]
    }


def get_clients_with_credit(db: Session) -> dict:
    """
    Clients who have a credit balance (overpaid, store owes them).
    Covers questions like:
    - "Which clients have credit with us?"
    - "Who overpaid?"
    - "Clients with positive credit balance"
    """
    accounts = db.query(ClientAccount).filter(
        ClientAccount.total_credit > 0
    ).order_by(desc(ClientAccount.total_credit)).all()
    return {
        "count": len(accounts),
        "clients": [
            {
                "client":       a.client.username if a.client else "unknown",
                "phone":        a.client.phone_number if a.client else None,
                "total_credit": float(a.total_credit),
            }
            for a in accounts
        ]
    }


# ══════════════════════════════════════════════════════════════
#  ADMIN — PRODUCTS & INVENTORY
# ══════════════════════════════════════════════════════════════

def get_low_stock_products(db: Session) -> dict:
    """
    Products at or below their minimum stock threshold.
    Covers questions like:
    - "What products need restocking?"
    - "Low inventory alert"
    - "Which products are running out?"
    - "Stock warning list"
    """
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_in_stock <= Product.minimum_stock_level
    ).order_by(asc(Product.quantity_in_stock)).all()
    return {
        "count": len(products),
        "products": [
            {
                "id":       p.id,
                "name":     p.name,
                "stock":    p.quantity_in_stock,
                "minimum":  p.minimum_stock_level,
                "category": p.category.name if p.category else "unknown",
                "price":    float(p.price),
            }
            for p in products
        ]
    }


def get_out_of_stock_products(db: Session) -> dict:
    """
    Products with zero stock.
    Covers questions like:
    - "What is out of stock?"
    - "Which products are unavailable?"
    - "Empty stock list"
    - "Products we can't sell right now"
    """
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.quantity_in_stock == 0
    ).all()
    return {
        "count": len(products),
        "products": [
            {
                "id":       p.id,
                "name":     p.name,
                "category": p.category.name if p.category else "unknown",
                "price":    float(p.price),
            }
            for p in products
        ]
    }


def search_any_product(db: Session, query: str) -> dict:
    """
    Search products by name — includes inactive products.
    Args:
        query: Product name or keyword to search.
    Covers questions like:
    - "Find product X"
    - "Do we carry [product name]?"
    - "Is [product] in our catalog?"
    - "Show me all versions of [product]"
    """
    products = db.query(Product).filter(
        Product.name.ilike(f"%{query}%")).limit(15).all()
    return {
        "count": len(products),
        "products": [
            {
                "id":            p.id,
                "name":          p.name,
                "price":         float(p.price),
                "stock":         p.quantity_in_stock,
                "minimum_stock": p.minimum_stock_level,
                "category":      p.category.name if p.category else "unknown",
                "is_active":     p.is_active,
                "is_on_sale":    p.is_sold,
                "barcode":       p.barcode,
            }
            for p in products
        ]
    }


def get_products_by_category(db: Session, category_name: str) -> dict:
    """
    All active products within a specific category.
    Args:
        category_name: Full or partial category name.
    Covers questions like:
    - "Show all products in [category]"
    - "What dental products do you have in [category]?"
    - "List products by type"
    """
    category = db.query(Category).filter(
        Category.name.ilike(f"%{category_name}%")).first()
    if not category:
        return {"error": f"Category '{category_name}' not found"}
    products = db.query(Product).filter(
        Product.category_id == category.id,
        Product.is_active == True
    ).all()
    return {
        "category":       category.name,
        "description":    category.description,
        "total_products": len(products),
        "products": [
            {
                "id":    p.id,
                "name":  p.name,
                "price": float(p.price),
                "stock": p.quantity_in_stock,
            }
            for p in products
        ]
    }


def get_all_categories_summary(db: Session) -> dict:
    """
    All product categories with product count per category.
    Covers questions like:
    - "What categories do you have?"
    - "How is the catalog organized?"
    - "Which category has the most products?"
    """
    categories = db.query(Category).all()
    return {
        "categories": [
            {
                "name":          c.name,
                "description":   c.description,
                "product_count": len([p for p in c.products if p.is_active]),
            }
            for c in categories
        ]
    }


def get_top_selling_products(db: Session) -> dict:
    """
    Top 10 products by total quantity sold across all bills.
    Covers questions like:
    - "What are our best-selling products?"
    - "Most popular items"
    - "Which products move the most?"
    - "Top products by sales volume"
    """
    results = db.query(
        BillItem.product_name,
        BillItem.product_id,
        func.sum(BillItem.quantity).label("total_qty"),
        func.sum(BillItem.subtotal).label("total_revenue"),
    ).group_by(BillItem.product_name, BillItem.product_id).order_by(desc("total_qty")).limit(10).all()
    return {
        "top_products": [
            {
                "product":              r.product_name,
                "total_quantity_sold":  int(r.total_qty),
                "total_revenue":        float(r.total_revenue),
            }
            for r in results
        ]
    }


def get_full_inventory(db: Session) -> dict:
    """
    Complete inventory list: all active products with current stock and price.
    Covers questions like:
    - "Show me the full inventory"
    - "List all products and their quantities"
    - "What do we currently have in stock?"
    """
    products = db.query(Product).filter(
        Product.is_active == True).order_by(Product.name).all()
    total_value = sum(float(p.price) * p.quantity_in_stock for p in products)
    return {
        "total_products":       len(products),
        "total_inventory_value": round(total_value, 2),
        "products": [
            {
                "id":       p.id,
                "name":     p.name,
                "category": p.category.name if p.category else "unknown",
                "price":    float(p.price),
                "stock":    p.quantity_in_stock,
                "minimum":  p.minimum_stock_level,
                "on_sale":  p.is_sold,
            }
            for p in products
        ]
    }


# ══════════════════════════════════════════════════════════════
#  ADMIN — PAYMENTS
# ══════════════════════════════════════════════════════════════

def get_recent_payments(db: Session) -> dict:
    """
    The 20 most recent payments with client name and method.
    Covers questions like:
    - "Show recent payments"
    - "Latest transactions"
    - "Who paid recently?"
    """
    payments = db.query(Payment).order_by(
        desc(Payment.payment_date)).limit(20).all()
    return {
        "payments": [
            {
                "id":          p.id,
                "bill_number": p.bill.bill_number if p.bill else "unknown",
                "client":      p.bill.client.username if p.bill and p.bill.client else "unknown",
                "amount":      float(p.amount_paid),
                "method":      p.payment_method,
                "notes":       p.notes,
                "date":        str(p.payment_date)[:10],
            }
            for p in payments
        ]
    }


def get_payments_today(db: Session) -> dict:
    """
    All payments received today with total collected.
    Covers questions like:
    - "How much did we collect today?"
    - "Today's payments"
    - "Cash received today"
    """
    today = datetime.now().date()
    payments = db.query(Payment).filter(
        func.date(Payment.payment_date) == today).all()
    return {
        "date":            str(today),
        "total_collected": float(sum(p.amount_paid for p in payments)),
        "payment_count":   len(payments),
        "payments": [
            {
                "bill_number": p.bill.bill_number if p.bill else "unknown",
                "client":      p.bill.client.username if p.bill and p.bill.client else "unknown",
                "amount":      float(p.amount_paid),
                "method":      p.payment_method,
            }
            for p in payments
        ]
    }


def get_payments_this_month(db: Session) -> dict:
    """
    Payment summary for the current month broken down by payment method.
    Covers questions like:
    - "Monthly collection report"
    - "How much cash vs bank transfer this month?"
    - "Total revenue collected this month"
    """
    now = datetime.now()
    payments = db.query(Payment).filter(
        extract("month", Payment.payment_date) == now.month,
        extract("year",  Payment.payment_date) == now.year,
    ).all()
    by_method: dict = {}
    for p in payments:
        m = p.payment_method or "unknown"
        by_method[m] = round(by_method.get(m, 0) + float(p.amount_paid), 2)
    return {
        "month":           now.strftime("%B %Y"),
        "total_collected": float(sum(p.amount_paid for p in payments)),
        "payment_count":   len(payments),
        "by_method":       by_method,
    }


def get_payment_method_breakdown(db: Session) -> dict:
    """
    All-time revenue broken down by payment method (cash, bank transfer, etc.).
    Covers questions like:
    - "How do clients usually pay?"
    - "Cash vs bank transfer breakdown"
    - "Payment method statistics"
    """
    results = db.query(
        Payment.payment_method,
        func.count(Payment.id).label("count"),
        func.sum(Payment.amount_paid).label("total"),
    ).group_by(Payment.payment_method).all()
    return {
        "breakdown": [
            {
                "method":        r.payment_method or "unknown",
                "payment_count": int(r.count),
                "total_amount":  float(r.total),
            }
            for r in results
        ]
    }


# ══════════════════════════════════════════════════════════════
#  ADMIN — STOCK ALERTS
# ══════════════════════════════════════════════════════════════

def get_unresolved_stock_alerts(db: Session) -> dict:
    """
    All stock alerts that have not been resolved yet.
    Covers questions like:
    - "What are the current stock alerts?"
    - "Any active inventory warnings?"
    - "Show unresolved stock issues"
    """
    alerts = db.query(StockAlert).filter(
        StockAlert.is_resolved == False
    ).order_by(desc(StockAlert.created_at)).all()
    return {
        "count": len(alerts),
        "alerts": [
            {
                "product":    a.product.name if a.product else "unknown",
                "stock":      a.product.quantity_in_stock if a.product else 0,
                "alert_type": a.alert_type,
                "message":    a.message,
                "created_at": str(a.created_at)[:10],
            }
            for a in alerts
        ]
    }


def get_all_stock_alerts(db: Session) -> dict:
    """
    Full stock alert history: both resolved and unresolved.
    Covers questions like:
    - "Stock alert history"
    - "How many stock alerts have we had?"
    - "Show all past and current stock warnings"
    """
    alerts = db.query(StockAlert).order_by(
        desc(StockAlert.created_at)).limit(50).all()
    return {
        "total":      len(alerts),
        "unresolved": sum(1 for a in alerts if not a.is_resolved),
        "resolved":   sum(1 for a in alerts if a.is_resolved),
        "alerts": [
            {
                "product":     a.product.name if a.product else "unknown",
                "alert_type":  a.alert_type,
                "message":     a.message,
                "is_resolved": a.is_resolved,
                "created_at":  str(a.created_at)[:10],
                "resolved_at": str(a.resolved_at)[:10] if a.resolved_at else None,
            }
            for a in alerts
        ]
    }


# ══════════════════════════════════════════════════════════════
#  CLIENT TOOLS  (scoped — db + client_id baked in by router)
# ══════════════════════════════════════════════════════════════

def get_client_bills(db: Session, client_id: int) -> dict:
    """Get all bills for the authenticated client."""
    bills = db.query(Bill).filter(
        Bill.client_id == client_id
    ).order_by(desc(Bill.created_at)).limit(20).all()
    return {
        "total": len(bills),
        "bills": [
            {
                "bill_number":     b.bill_number,
                "total_amount":    float(b.total_amount),
                "total_paid":      float(b.total_paid),
                "total_remaining": float(b.total_remaining),
                "status":          b.status,
                "delivery_status": b.delivery_status,
                "created_at":      str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_client_unpaid_bills(db: Session, client_id: int) -> dict:
    """Get only unpaid bills for the authenticated client."""
    bills = db.query(Bill).filter(
        Bill.client_id == client_id,
        Bill.status == "not paid"
    ).all()
    return {
        "unpaid_count":    len(bills),
        "total_remaining": float(sum(b.total_remaining for b in bills)),
        "bills": [
            {
                "bill_number":     b.bill_number,
                "total_amount":    float(b.total_amount),
                "total_remaining": float(b.total_remaining),
                "created_at":      str(b.created_at)[:10],
            }
            for b in bills
        ]
    }


def get_client_account_summary(db: Session, client_id: int) -> dict:
    """Get financial account summary for the authenticated client."""
    account = db.query(ClientAccount).filter(
        ClientAccount.client_id == client_id).first()
    if not account:
        return {"error": "No account found"}
    return {
        "total_amount":    float(account.total_amount),
        "total_paid":      float(account.total_paid),
        "total_remaining": float(account.total_remaining),
        "total_credit":    float(account.total_credit),
    }


def get_bill_details_for_client(db: Session, client_id: int, bill_number: str) -> dict:
    """Get full details of a specific bill owned by the authenticated client."""
    bill = db.query(Bill).filter(
        Bill.client_id == client_id,
        Bill.bill_number == bill_number
    ).first()
    if not bill:
        return {"error": "Bill not found or does not belong to you"}
    return {
        "bill_number":     bill.bill_number,
        "status":          bill.status,
        "delivery_status": bill.delivery_status,
        "total_amount":    float(bill.total_amount),
        "total_paid":      float(bill.total_paid),
        "total_remaining": float(bill.total_remaining),
        "created_at":      str(bill.created_at)[:10],
        "items": [
            {
                "product_name": item.product_name,
                "quantity":     item.quantity,
                "unit_price":   float(item.unit_price),
                "subtotal":     float(item.subtotal),
                "deep_link":    f"myapp://product/{item.product_id}" if item.product_id else None,
            }
            for item in bill.bill_items
        ]
    }


def search_products_for_client(db: Session, query: str) -> dict:
    """Search active products visible to clients."""
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.name.ilike(f"%{query}%")
    ).limit(8).all()
    return {
        "products": [
            {
                "id":       p.id,
                "name":     p.name,
                "price":    float(p.price),
                "in_stock": p.quantity_in_stock > 0,
                "on_sale":  p.is_sold,
                "category": p.category.name if p.category else "unknown",
                "deep_link": f"myapp://product/{p.id}",
            }
            for p in products
        ]
    }


def get_active_categories_for_client(db: Session) -> dict:
    """Get all categories that have at least one active product."""
    categories = db.query(Category).all()
    result = [
        {
            "name":          c.name,
            "description":   c.description,
            "product_count": len([p for p in c.products if p.is_active]),
        }
        for c in categories
        if any(p.is_active for p in c.products)
    ]
    return {"categories": result}


def get_products_by_category_for_client(db: Session, category_name: str) -> dict:
    """Get active products in a category — client-facing (no stock numbers)."""
    category = db.query(Category).filter(
        Category.name.ilike(f"%{category_name}%")).first()
    if not category:
        return {"error": f"Category '{category_name}' not found"}
    products = db.query(Product).filter(
        Product.category_id == category.id,
        Product.is_active == True
    ).all()
    return {
        "category":       category.name,
        "total_products": len(products),
        "products": [
            {
                "id":       p.id,
                "name":     p.name,
                "price":    float(p.price),
                "in_stock": p.quantity_in_stock > 0,
                "on_sale":  p.is_sold,
                "deep_link": f"myapp://product/{p.id}",
            }
            for p in products
        ]
    }
