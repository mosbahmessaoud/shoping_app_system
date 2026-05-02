# routers/chat.py
"""
AI Chat endpoints powered by Groq (llama-3.3-70b-versatile).

| Endpoint      | Who   | Access scope                              |
|---------------|-------|-------------------------------------------|
| POST /chat/client | Client | Own bills, account, products (read-only) |
| POST /chat/admin  | Admin  | Full business data                        |

Authentication:
  - Uncomment the `Depends(get_current_*)` lines once JWT auth is wired up.
  - Tools are defined as closures so db + client_id are baked in — the AI
    cannot leak data across users even if it tries to pass different IDs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from utils.db import get_db
from services.ai_chat import chat_with_gemini          # Groq under the hood
from services.ai_tools_gemini import (
    # ── Admin tools ──────────────────────────────────────────
    get_dashboard_stats,
    get_all_bills_with_status,
    get_unpaid_bills,
    get_bills_today,
    get_bills_this_month,
    get_bills_last_7_days,
    get_bill_details_by_number,
    get_bills_by_client_name,
    get_delivery_status_summary,
    get_bills_not_delivered,
    get_all_clients_summary,
    get_client_details,
    get_top_clients_by_debt,
    get_top_clients_by_revenue,
    get_clients_with_credit,
    get_low_stock_products,
    get_out_of_stock_products,
    search_any_product,
    get_products_by_category,
    get_all_categories_summary,
    get_top_selling_products,
    get_full_inventory,
    get_recent_payments,
    get_payments_today,
    get_payments_this_month,
    get_payment_method_breakdown,
    get_unresolved_stock_alerts,
    get_all_stock_alerts,
    # ── Client tools ─────────────────────────────────────────
    get_client_bills,
    get_client_unpaid_bills,
    get_client_account_summary,
    get_bill_details_for_client,
    search_products_for_client,
    get_active_categories_for_client,
    get_products_by_category_for_client,
)

# from routers.auth import get_current_client, get_current_admin  # ← uncomment when auth ready

router = APIRouter(prefix="/chat", tags=["AI Chat"])


# ══════════════════════════════════════════════════════════════
#  Request / Response schemas
# ══════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str        # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


# ══════════════════════════════════════════════════════════════
#  System prompts
# ══════════════════════════════════════════════════════════════

CLIENT_SYSTEM_PROMPT = """
You are a helpful AI assistant for clients of this dental products store.

## Your Rules
- You can ONLY access data that belongs to the currently authenticated client.
- NEVER reveal data about other clients, internal business metrics, or admin information.
- If asked about restricted information, politely explain you don't have access to that.

## What You Can Help With
| Topic               | Examples                                              |
|---------------------|-------------------------------------------------------|
| My bills            | Status, amounts, items, delivery tracking             |
| My account balance  | Total owed, paid, remaining, credit                   |
| Product search      | Find dental products by name or category              |
| Browse catalog      | List categories, products in a category               |
| Unpaid invoices     | What I still owe                                      |

## Product Deep Links
When a product has a `deep_link`, always show it as a tappable button:
👉 [VIEW PRODUCT](deep_link_url)

## Response Style
- Use **tables** or **bullet points** — avoid long paragraphs.
- Be concise, friendly, and clear.
- Always respond in the **same language the user writes in** (Arabic, French, or English).
- For numbers, always show the currency unit (DZD or DA).
"""

ADMIN_SYSTEM_PROMPT = """
You are a business intelligence assistant for the store admin.
You have FULL access to all business data.

## What You Can Help With
| Category         | Examples of questions                                             |
|------------------|-------------------------------------------------------------------|
| Dashboard        | Overall revenue, bill counts, stock health, client count         |
| Bills            | Today's bills, unpaid list, bill details, delivery status        |
| Clients          | Client profile, top debtors, top buyers, credit balances         |
| Products         | Inventory, low stock, out of stock, top sellers, by category     |
| Payments         | Today's collections, monthly totals, payment method breakdown    |
| Stock alerts     | Unresolved alerts, full alert history                            |

## Response Style
- Always use **tables**, **bullet lists**, or **structured sections** — no long paragraphs.
- **Proactively flag issues**: if a query reveals low stock or high debt, mention it.
- For monetary values, show the amount with currency (DZD / DA).
- Always respond in the **same language the admin writes in** (Arabic, French, or English).
- When data is empty, say so clearly rather than showing an empty result.

## Example Good Response Format
> 📊 **Monthly Summary — May 2025**
> | Metric         | Value     |
> |----------------|-----------|
> | Total bills    | 42        |
> | Paid           | 30 (71%)  |
> | Remaining      | 85,000 DA |
> ⚠️ 3 products are currently out of stock.
"""


# ══════════════════════════════════════════════════════════════
#  CLIENT Chat Endpoint
# ══════════════════════════════════════════════════════════════

@router.post("/client", summary="Chat for authenticated clients")
async def client_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    # current_client = Depends(get_current_client),  # ← uncomment when auth ready
):
    """
    Handles client questions. Tools are closures — db and client_id
    are baked in so the AI cannot access other clients' data.

    Supported questions (examples):
    - "What are my unpaid bills?"
    - "Show me the details of bill BILL-042"
    - "What is my current balance?"
    - "Search for dental gloves"
    - "What products do you have in the prosthetics category?"
    - "Has my order been delivered?"
    - "How much do I still owe?"
    - "Do you have [product name] in stock?"
    """
    # Replace with: client_id = current_client.id
    client_id = 1

    # ── Tools as closures (db + client_id locked in) ──────────

    def get_my_bills() -> dict:
        """
        Get all my bills with payment status and delivery status.
        Use when asked: 'my orders', 'my invoices', 'my bills', 'order history'.
        """
        return get_client_bills(db, client_id)

    def get_my_unpaid_bills() -> dict:
        """
        Get only my unpaid bills and total remaining balance.
        Use when asked: 'what do I owe?', 'unpaid invoices', 'my debt', 'remaining balance'.
        """
        return get_client_unpaid_bills(db, client_id)

    def get_my_account_summary() -> dict:
        """
        Get my full financial summary: total purchased, paid, remaining, and any credit.
        Use when asked: 'my account', 'my balance', 'how much have I spent?', 'do I have credit?'.
        """
        return get_client_account_summary(db, client_id)

    def get_my_bill_details(bill_number: str) -> dict:
        """
        Get item-by-item breakdown of one specific bill.
        Args:
            bill_number: The bill number (e.g. BILL-001).
        Use when asked: 'details of bill X', 'what is in invoice X?', 'show bill X'.
        """
        return get_bill_details_for_client(db, client_id, bill_number)

    def search_products(query: str) -> dict:
        """
        Search for products available in the store by name or keyword.
        Args:
            query: Product name or keyword (e.g. 'gloves', 'dental mirror', 'composite').
        Use when asked: 'do you have X?', 'find product Y', 'search for Z'.
        """
        return search_products_for_client(db, query)

    def browse_categories() -> dict:
        """
        List all product categories with product counts.
        Use when asked: 'what categories do you have?', 'types of products',
        'what do you sell?', 'show me the catalog'.
        """
        return get_active_categories_for_client(db)

    def get_products_in_category(category_name: str) -> dict:
        """
        Get all products in a specific category.
        Args:
            category_name: Category name (e.g. 'prosthetics', 'instruments', 'consumables').
        Use when asked: 'show products in [category]', 'what is in [category]?'.
        """
        return get_products_by_category_for_client(db, category_name)

    # ── Build and call ────────────────────────────────────────

    messages = [m.dict() for m in request.history] + [
        {"role": "user", "content": request.message}
    ]

    reply = chat_with_gemini(
        messages=messages,
        tool_functions=[
            get_my_bills,
            get_my_unpaid_bills,
            get_my_account_summary,
            get_my_bill_details,
            search_products,
            browse_categories,
            get_products_in_category,
        ],
        system_prompt=CLIENT_SYSTEM_PROMPT,
    )

    return {"reply": reply}


# ══════════════════════════════════════════════════════════════
#  ADMIN Chat Endpoint
# ══════════════════════════════════════════════════════════════

@router.post("/admin", summary="Chat for store admin")
async def admin_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    # current_admin = Depends(get_current_admin),  # ← uncomment when auth ready
):
    """
    Handles admin business intelligence questions.
    Full access to all store data.

    Supported questions (examples):
    Dashboard:
    - "Give me a business overview"
    - "How is the store doing?"

    Bills:
    - "Show all unpaid bills"
    - "How many bills did we make today / this month?"
    - "Sales trend last 7 days"
    - "Details of bill BILL-042"
    - "All bills for client Ahmed"
    - "Which orders haven't been delivered yet?"
    - "Delivery status breakdown"

    Clients:
    - "List all clients"
    - "Tell me about client [name]"
    - "Who owes us the most money?"
    - "Top 10 buyers by revenue"
    - "Which clients have credit?"

    Products & Inventory:
    - "Show full inventory"
    - "What products are low on stock?"
    - "What is out of stock?"
    - "Search for [product name]"
    - "Products in [category name]"
    - "All categories"
    - "Best-selling products"

    Payments:
    - "How much did we collect today?"
    - "Monthly payment report"
    - "Recent payments list"
    - "Cash vs bank transfer breakdown"

    Stock Alerts:
    - "Any active stock alerts?"
    - "Show all stock alert history"
    """

    # ── Tools as closures (db locked in) ─────────────────────

    # — Dashboard —
    def get_stats() -> dict:
        """
        Full business dashboard: revenue, bills, clients, stock health.
        Use for: 'overview', 'how is the store?', 'summary', 'dashboard'.
        """
        return get_dashboard_stats(db)

    # — Bills —
    def list_all_bills() -> dict:
        """
        Last 50 bills with status, client name, and amounts.
        Use for: 'show all bills', 'recent bills', 'bill list'.
        """
        return get_all_bills_with_status(db)

    def list_unpaid_bills() -> dict:
        """
        All unpaid bills sorted by highest remaining amount.
        Use for: 'unpaid invoices', 'who still owes?', 'outstanding balances'.
        """
        return get_unpaid_bills(db)

    def bills_today() -> dict:
        """
        All bills created today.
        Use for: 'today sales', 'today orders', 'daily bills'.
        """
        return get_bills_today(db)

    def bills_this_month() -> dict:
        """
        Monthly bill and revenue summary.
        Use for: 'monthly report', 'this month sales', 'monthly performance'.
        """
        return get_bills_this_month(db)

    def bills_last_7_days() -> dict:
        """
        Bills grouped by day for the last 7 days.
        Use for: 'weekly trend', 'last week', '7-day overview'.
        """
        return get_bills_last_7_days(db)

    def bill_details(bill_number: str) -> dict:
        """
        Full breakdown of a specific bill including items and payment history.
        Args:
            bill_number: Bill number to look up (e.g. BILL-001).
        Use for: 'details of bill X', 'show invoice X', 'what is in bill X?'.
        """
        return get_bill_details_by_number(db, bill_number)

    def bills_for_client(client_name: str) -> dict:
        """
        All bills belonging to a specific client.
        Args:
            client_name: Full or partial client name.
        Use for: 'bills for [name]', 'orders from [name]', '[name] invoice history'.
        """
        return get_bills_by_client_name(db, client_name)

    def delivery_summary() -> dict:
        """
        Count of bills by delivery status: delivered / on_the_way / not_delivered.
        Use for: 'delivery status', 'shipping overview', 'how many delivered?'.
        """
        return get_delivery_status_summary(db)

    def undelivered_bills() -> dict:
        """
        All bills that have NOT been delivered yet.
        Use for: 'pending deliveries', 'not delivered', 'orders to ship'.
        """
        return get_bills_not_delivered(db)

    # — Clients —
    def list_clients() -> dict:
        """
        All active clients with balance info.
        Use for: 'client list', 'all customers', 'clients with balances'.
        """
        return get_all_clients_summary(db)

    def client_profile(client_name: str) -> dict:
        """
        Full profile and account details for a specific client.
        Args:
            client_name: Full or partial name.
        Use for: 'info about [name]', '[name] profile', '[name] account'.
        """
        return get_client_details(db, client_name)

    def top_debtors() -> dict:
        """
        Top 10 clients with the highest unpaid balances.
        Use for: 'who owes the most?', 'highest debt', 'top debtors', 'unpaid clients'.
        """
        return get_top_clients_by_debt(db)

    def top_buyers() -> dict:
        """
        Top 10 clients by total amount purchased.
        Use for: 'best clients', 'top buyers', 'VIP customers', 'highest spending'.
        """
        return get_top_clients_by_revenue(db)

    def clients_with_credit() -> dict:
        """
        Clients who have a credit balance (store owes them money back).
        Use for: 'clients with credit', 'who overpaid?', 'credit balances'.
        """
        return get_clients_with_credit(db)

    # — Products & Inventory —
    def full_inventory() -> dict:
        """
        Complete active product list with stock levels and prices.
        Use for: 'full inventory', 'all products', 'stock list', 'product catalog'.
        """
        return get_full_inventory(db)

    def low_stock() -> dict:
        """
        Products at or below their minimum stock threshold.
        Use for: 'low stock', 'need to reorder', 'stock warnings', 'running out'.
        """
        return get_low_stock_products(db)

    def out_of_stock() -> dict:
        """
        Products with zero quantity in stock.
        Use for: 'out of stock', 'unavailable products', 'empty stock'.
        """
        return get_out_of_stock_products(db)

    def search_products(query: str) -> dict:
        """
        Search any product by name including inactive ones.
        Args:
            query: Product name or keyword.
        Use for: 'find [product]', 'search [name]', 'do we have [product]?'.
        """
        return search_any_product(db, query)

    def products_in_category(category_name: str) -> dict:
        """
        All active products within a specific category.
        Args:
            category_name: Full or partial category name.
        Use for: 'products in [category]', 'what is in [category]?'.
        """
        return get_products_by_category(db, category_name)

    def all_categories() -> dict:
        """
        All categories with product count per category.
        Use for: 'list categories', 'how many products per category', 'catalog structure'.
        """
        return get_all_categories_summary(db)

    def top_selling_products() -> dict:
        """
        Top 10 best-selling products by quantity sold.
        Use for: 'best sellers', 'most popular products', 'top items', 'what sells most?'.
        """
        return get_top_selling_products(db)

    # — Payments —
    def recent_payments() -> dict:
        """
        Last 20 payments with client name, amount, and method.
        Use for: 'recent payments', 'latest transactions', 'who paid recently?'.
        """
        return get_recent_payments(db)

    def payments_today() -> dict:
        """
        All payments received today with total.
        Use for: 'today collections', 'daily revenue', 'payments today'.
        """
        return get_payments_today(db)

    def payments_this_month() -> dict:
        """
        Monthly payment summary broken down by payment method.
        Use for: 'monthly collections', 'revenue this month', 'monthly payment report'.
        """
        return get_payments_this_month(db)

    def payment_methods_breakdown() -> dict:
        """
        All-time payment totals grouped by method (cash, bank transfer, etc.).
        Use for: 'how do clients pay?', 'cash vs transfer', 'payment method stats'.
        """
        return get_payment_method_breakdown(db)

    # — Stock Alerts —
    def active_stock_alerts() -> dict:
        """
        All unresolved stock alerts currently active.
        Use for: 'stock alerts', 'inventory warnings', 'active alerts'.
        """
        return get_unresolved_stock_alerts(db)

    def stock_alert_history() -> dict:
        """
        Full stock alert history including resolved ones.
        Use for: 'alert history', 'past stock issues', 'all stock alerts'.
        """
        return get_all_stock_alerts(db)

    # ── Build and call ────────────────────────────────────────

    messages = [m.dict() for m in request.history] + [
        {"role": "user", "content": request.message}
    ]

    reply = chat_with_gemini(
        messages=messages,
        tool_functions=[
            # Dashboard
            get_stats,
            # Bills
            list_all_bills,
            list_unpaid_bills,
            bills_today,
            bills_this_month,
            bills_last_7_days,
            bill_details,
            bills_for_client,
            delivery_summary,
            undelivered_bills,
            # Clients
            list_clients,
            client_profile,
            top_debtors,
            top_buyers,
            clients_with_credit,
            # Products & Inventory
            full_inventory,
            low_stock,
            out_of_stock,
            search_products,
            products_in_category,
            all_categories,
            top_selling_products,
            # Payments
            recent_payments,
            payments_today,
            payments_this_month,
            payment_methods_breakdown,
            # Stock alerts
            active_stock_alerts,
            stock_alert_history,
        ],
        system_prompt=ADMIN_SYSTEM_PROMPT,
    )

    return {"reply": reply}
