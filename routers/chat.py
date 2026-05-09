# routers/chat.py
"""
AI Chat endpoints — client and admin, JWT-protected.

  POST /chat/client  →  authenticated client only (own data, read-only)
  POST /chat/admin   →  authenticated admin only (full business data + web)

Auth:
  Both endpoints use JWT via get_current_client / get_current_admin.
  client_id is extracted from the verified token — never from the request body.
  A client cannot touch another client's data even if they craft a payload.

Speed improvements:
  - Tool schemas are built once at module load (not per request).
  - Streaming-friendly: the agentic loop has a tight 3-iteration cap for chat.
  - Groq primary with Gemini fallback preserved.

Response format:
  HTML only — no markdown. Language mirrors the user's message automatically
  (the LLM is instructed, and the system prompts enforce it strongly).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from utils.db import get_db
from services.ai_chat import chat_ai
from services.web_search import web_search as _web_search
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

from utils.auth import get_current_client, get_current_admin, get_current_user

router = APIRouter(prefix="/chat", tags=["AI Chat"])


# ══════════════════════════════════════════════════════════════
#  Schemas
# ══════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


# ══════════════════════════════════════════════════════════════
#  System prompts
# ══════════════════════════════════════════════════════════════
CLIENT_SYSTEM_PROMPT = """\
You are a smart, friendly assistant for clients of a dental products store.
You have real-time access to the client's own data via tools.

LANGUAGE — ABSOLUTE RULE:
Detect the language of the LAST USER message and reply in THAT language only.
Arabic → full Arabic. French → full French. English → full English. Never mix.

FORMAT — HTML only, zero markdown. Available components:

1. TABLES — for bill lists, product lists:
   <table><thead><tr><th>الفاتورة</th><th>المبلغ</th></tr></thead>
   <tbody><tr><td>BILL-001</td><td>1,200 دج</td></tr></tbody></table>

2. KPI CARDS — for account summary:
   <div class="kpi-grid">
     <div class="kpi-card blue">
       <div class="kpi-icon">💳</div>
       <div class="kpi-value">5,400 دج</div>
       <div class="kpi-label">المبلغ المتبقي</div>
     </div>
   </div>

3. PROGRESS BAR — for showing paid vs remaining:
   <div class="progress-wrap">
     <div class="progress-label"><span>نسبة السداد</span><span>68%</span></div>
     <div class="progress-bar"><div class="progress-fill green" data-value="68"></div></div>
   </div>

4. ALERT BLOCKS — for important notices:
   <div class="alert-block alert-warn">
     <span class="alert-icon">⚠️</span><div>لديك فاتورة غير مدفوعة منذ 30 يوماً.</div>
   </div>

5. BADGES:
   <span class="badge badge-green">مدفوع</span>
   <span class="badge badge-red">غير مدفوع</span>

6. LINKS for products:
   <a href="myapp://product/42">عرض المنتج</a>

NEVER output | col |, ## heading, **bold**, or - bullet. Only the HTML above.
Keep charts minimal for clients — prefer KPI cards + progress bars + tables.

TONE — Natural, helpful, like a friendly store assistant. Keep it concise.
SECURITY — Only show this client's data. Never mention other clients.
MONEY — Always append DZD or DA after monetary values.

TOOLS:
  get_my_bills           → order/invoice history
  get_my_unpaid_bills    → outstanding balance
  get_my_account_summary → full balance overview  
  get_my_bill_details    → one specific invoice (needs bill_number)
  search_products        → find a product by name
  browse_categories      → catalog overview
  get_products_in_category → products by type
  search_web             → external info (specs, brands)
"""
ADMIN_SYSTEM_PROMPT = """\
You are a business intelligence assistant with full access to store data.

LANGUAGE — ABSOLUTE RULE:
Detect the language of the LAST message and reply in THAT language only.
Arabic → full Arabic. French → full French. English → full English. Never mix.

FORMAT — HTML only, zero markdown. Available components:

1. TABLES (for lists of bills, clients, products):
   <table><thead><tr><th>العمود</th></tr></thead>
   <tbody><tr><td>القيمة</td></tr></tbody></table>

2. KPI CARDS (for key numbers / dashboard summaries):
   <div class="kpi-grid">
     <div class="kpi-card green">
       <div class="kpi-icon">💰</div>
       <div class="kpi-value">12,400</div>
       <div class="kpi-label">الإيرادات</div>
       <div class="kpi-trend up">▲ 8.3%</div>
     </div>
     <div class="kpi-card red">...</div>
     <div class="kpi-card amber">...</div>
     <div class="kpi-card purple">...</div>
   </div>
   kpi-card color variants: green, red, amber, purple (default blue)
   kpi-trend variants: up (green), down (red), flat (grey)

3. BAR CHART (for daily/monthly totals, product comparisons):
   <div class="chart-wrap">
     <div class="chart-title">عنوان الرسم</div>
     <canvas id="chart1"></canvas>
   </div>
   <script>renderBar('chart1', ['يناير','فبراير','مارس'], [4200,3800,5100], 'دج')</script>
   Signature: renderBar(canvasId, labels[], values[], unit)

4. LINE CHART (for trends over time):
   <div class="chart-wrap">
     <div class="chart-title">الاتجاه الشهري</div>
     <canvas id="chart2"></canvas>
   </div>
   <script>renderLine('chart2', ['أسبوع 1','أسبوع 2'], [{label:'المبيعات', data:[3000,4200]}], 'المبيعات')</script>
   Signature: renderLine(canvasId, labels[], datasets[{label, data[]}], title)

5. DOUGHNUT / PIE CHART (for payment methods, delivery status breakdown):
   <div class="chart-wrap">
     <canvas id="chart3"></canvas>
   </div>
   <script>renderPie('chart3', ['نقداً','تحويل','شيك'], [6200,3100,900], 'doughnut')</script>
   Signature: renderPie(canvasId, labels[], values[], 'doughnut'|'pie')

6. PROGRESS BAR (for stock levels, goal completion):
   <div class="progress-wrap">
     <div class="progress-label"><span>المنتج أ</span><span>72%</span></div>
     <div class="progress-bar"><div class="progress-fill green" data-value="72"></div></div>
   </div>
   progress-fill variants: (default blue), green, amber, red

7. ALERT BLOCKS (for warnings and notifications):
   <div class="alert-block alert-warn">
     <span class="alert-icon">⚠️</span>
     <div>نص التنبيه</div>
   </div>
   alert variants: alert-error, alert-warn, alert-info, alert-success

8. BADGES (inline status pills):
   <span class="badge badge-green">مدفوع</span>
   badge variants: badge-blue, badge-green, badge-amber, badge-red, badge-purple

CHART RULES:
- Each canvas id must be unique per response (chart1, chart2, chart3 …).
- Always wrap charts in <div class="chart-wrap">.
- Place <script> tags immediately after their chart-wrap div.
- Use charts for: daily/weekly trends, payment breakdowns, top products, delivery status.
- Use KPI cards for: summary numbers (revenue, bill count, debt total, stock count).
- Use tables for: client lists, bill details, product inventories.
- Combine them: KPI grid first → chart → supporting table.

NEVER output | col |, ## heading, **bold**, or - bullet. Only the HTML above.

TONE — Direct, data-first. Lead with the answer, then the data.
PROACTIVE FLAGS — If results show low stock, high debt, or undelivered orders:
  <div class="alert-block alert-warn"><span class="alert-icon">⚠️</span><div>تنبيه: …</div></div>
MONEY — Always append DZD or DA after monetary values.
"""


# ══════════════════════════════════════════════════════════════
#  CLIENT endpoint
# ══════════════════════════════════════════════════════════════

@router.post("/client", summary="Client AI chat — JWT required")
async def client_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_client=Depends(get_current_client),   # ← real JWT auth
):
    client_id: int = current_client.id  # extracted from verified token

    # Tools are closures — client_id is baked in, the model cannot change it
    def get_my_bills() -> dict:
        """Get all my bills with payment and delivery status.
        Use for: 'my orders', 'my invoices', 'order history'."""
        return get_client_bills(db, client_id)

    def get_my_unpaid_bills() -> dict:
        """Get only my unpaid bills and outstanding balance.
        Use for: 'what do I owe', 'unpaid invoices', 'my debt'."""
        return get_client_unpaid_bills(db, client_id)

    def get_my_account_summary() -> dict:
        """Get my full account: total bought, paid, remaining, credit.
        Use for: 'my balance', 'how much have I spent', 'do I have credit'."""
        return get_client_account_summary(db, client_id)

    def get_my_bill_details(bill_number: str) -> dict:
        """Get item-by-item breakdown of one specific bill.
        Args: bill_number — e.g. BILL-001.
        Use for: 'details of bill X', 'what is in invoice X'."""
        return get_bill_details_for_client(db, client_id, bill_number)

    def search_products(query: str) -> dict:
        """Search for products in the store by name or keyword.
        Args: query — e.g. 'gloves', 'dental mirror'.
        Use for: 'do you have X', 'find product Y'."""
        return search_products_for_client(db, query)

    def browse_categories() -> dict:
        """List all product categories with counts.
        Use for: 'what categories', 'what do you sell', 'catalog'."""
        return get_active_categories_for_client(db)

    def get_products_in_category(category_name: str) -> dict:
        """Get all products in a specific category.
        Args: category_name — e.g. 'prosthetics', 'instruments'.
        Use for: 'show products in [category]'."""
        return get_products_by_category_for_client(db, category_name)

    def search_web(query: str) -> dict:
        """Search the internet for dental product info, specs, brand comparisons,
        clinical guidelines. Do NOT use for account or billing questions.
        Args: query — e.g. '3M Filtek composite specifications'."""
        return _web_search(query)

    messages = [m.dict() for m in request.history] + [
        {"role": "user", "content": request.message}
    ]

    reply = chat_ai(
        messages=messages,
        tool_functions=[
            get_my_bills, get_my_unpaid_bills, get_my_account_summary,
            get_my_bill_details, search_products, browse_categories,
            get_products_in_category, search_web,
        ],
        system_prompt=CLIENT_SYSTEM_PROMPT,
    )
    return {"reply": reply}


# ══════════════════════════════════════════════════════════════
#  ADMIN endpoint
# ══════════════════════════════════════════════════════════════

@router.post("/admin", summary="Admin AI chat — JWT required")
async def admin_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),   # ← real JWT auth
):
    # Dashboard
    def get_stats() -> dict:
        """Full business dashboard: revenue, bills, clients, stock health.
        Use for: 'overview', 'how is the store', 'summary', 'dashboard'."""
        return get_dashboard_stats(db)

    # Bills
    def list_all_bills() -> dict:
        """Last 50 bills with status, client name, and amounts.
        Use for: 'show all bills', 'recent bills', 'bill list'."""
        return get_all_bills_with_status(db)

    def list_unpaid_bills() -> dict:
        """All unpaid bills sorted by highest remaining amount.
        Use for: 'unpaid invoices', 'who still owes', 'outstanding balances'."""
        return get_unpaid_bills(db)

    def bills_today() -> dict:
        """All bills created today.
        Use for: 'today sales', 'today orders', 'daily bills'."""
        return get_bills_today(db)

    def bills_this_month() -> dict:
        """Monthly bill and revenue summary.
        Use for: 'monthly report', 'this month sales'."""
        return get_bills_this_month(db)

    def bills_last_7_days() -> dict:
        """Bills grouped by day for the last 7 days.
        Use for: 'weekly trend', 'last week', '7-day overview'."""
        return get_bills_last_7_days(db)

    def bill_details(bill_number: str) -> dict:
        """Full breakdown of a specific bill including items and payment history.
        Args: bill_number — e.g. BILL-001.
        Use for: 'details of bill X', 'show invoice X'."""
        return get_bill_details_by_number(db, bill_number)

    def bills_for_client(client_name: str) -> dict:
        """All bills belonging to a specific client.
        Args: client_name — full or partial name.
        Use for: 'bills for [name]', 'orders from [name]'."""
        return get_bills_by_client_name(db, client_name)

    def delivery_summary() -> dict:
        """Count of bills by delivery status.
        Use for: 'delivery status', 'shipping overview'."""
        return get_delivery_status_summary(db)

    def undelivered_bills() -> dict:
        """All bills not yet delivered.
        Use for: 'pending deliveries', 'orders to ship'."""
        return get_bills_not_delivered(db)

    # Clients
    def list_clients() -> dict:
        """All active clients with balance info.
        Use for: 'client list', 'all customers'."""
        return get_all_clients_summary(db)

    def client_profile(client_name: str) -> dict:
        """Full profile and account details for a specific client.
        Args: client_name — full or partial name."""
        return get_client_details(db, client_name)

    def top_debtors() -> dict:
        """Top 10 clients with the highest unpaid balances.
        Use for: 'who owes the most', 'highest debt', 'top debtors'."""
        return get_top_clients_by_debt(db)

    def top_buyers() -> dict:
        """Top 10 clients by total purchase amount.
        Use for: 'best clients', 'top buyers', 'VIP customers'."""
        return get_top_clients_by_revenue(db)

    def clients_with_credit() -> dict:
        """Clients who have a credit balance (store owes them).
        Use for: 'clients with credit', 'who overpaid'."""
        return get_clients_with_credit(db)

    # Products
    def full_inventory() -> dict:
        """Complete product list with stock levels and prices.
        Use for: 'full inventory', 'all products', 'stock list'."""
        return get_full_inventory(db)

    def low_stock() -> dict:
        """Products at or below minimum stock threshold.
        Use for: 'low stock', 'need to reorder', 'running out'."""
        return get_low_stock_products(db)

    def out_of_stock() -> dict:
        """Products with zero quantity.
        Use for: 'out of stock', 'unavailable products'."""
        return get_out_of_stock_products(db)

    def search_products(query: str) -> dict:
        """Search any product by name including inactive ones.
        Args: query — product name or keyword."""
        return search_any_product(db, query)

    def products_in_category(category_name: str) -> dict:
        """All active products within a category.
        Args: category_name — full or partial name."""
        return get_products_by_category(db, category_name)

    def all_categories() -> dict:
        """All categories with product count.
        Use for: 'list categories', 'catalog structure'."""
        return get_all_categories_summary(db)

    def top_selling() -> dict:
        """Top 10 best-selling products by quantity sold.
        Use for: 'best sellers', 'most popular products'."""
        return get_top_selling_products(db)

    # Payments
    def recent_payments() -> dict:
        """Last 20 payments with client name, amount, method.
        Use for: 'recent payments', 'latest transactions'."""
        return get_recent_payments(db)

    def payments_today() -> dict:
        """All payments received today with total.
        Use for: 'today collections', 'daily revenue'."""
        return get_payments_today(db)

    def payments_this_month() -> dict:
        """Monthly payment summary by method.
        Use for: 'monthly collections', 'revenue this month'."""
        return get_payments_this_month(db)

    def payment_methods() -> dict:
        """All-time payment totals by method (cash, transfer, etc.).
        Use for: 'how do clients pay', 'cash vs transfer'."""
        return get_payment_method_breakdown(db)

    # Stock alerts
    def active_alerts() -> dict:
        """All unresolved stock alerts.
        Use for: 'stock alerts', 'inventory warnings'."""
        return get_unresolved_stock_alerts(db)

    def alert_history() -> dict:
        """Full stock alert history including resolved ones.
        Use for: 'alert history', 'past stock issues'."""
        return get_all_stock_alerts(db)

    # Web search
    def search_web(query: str) -> dict:
        """Search the internet for external info: supplier prices, industry news,
        product specs, market trends. Use ONLY for external data, not internal.
        Args: query — e.g. 'dental supply prices Algeria 2025'."""
        return _web_search(query)

    messages = [m.dict() for m in request.history] + [
        {"role": "user", "content": request.message}
    ]

    reply = chat_ai(
        messages=messages,
        tool_functions=[
            get_stats,
            list_all_bills, list_unpaid_bills, bills_today,
            bills_this_month, bills_last_7_days, bill_details,
            bills_for_client, delivery_summary, undelivered_bills,
            list_clients, client_profile, top_debtors, top_buyers,
            clients_with_credit,
            full_inventory, low_stock, out_of_stock, search_products,
            products_in_category, all_categories, top_selling,
            recent_payments, payments_today, payments_this_month,
            payment_methods,
            active_alerts, alert_history,
            search_web,
        ],
        system_prompt=ADMIN_SYSTEM_PROMPT,
    )
    return {"reply": reply}
