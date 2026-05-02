# routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from utils.db import get_db
from services.ai_chat import chat_with_gemini
from services.ai_tools_gemini import (
    get_all_bills_with_status,
    get_client_bills,
    get_client_account_summary,
    search_products_for_client,
    get_bill_details_for_client,
    get_dashboard_stats,
    get_all_clients_summary,
    get_low_stock_products,
    search_any_product,
    get_recent_payments,
)

# ── Uncomment these when you wire up your JWT auth ──────────
# from routers.auth import get_current_client, get_current_admin

router = APIRouter(prefix="/chat", tags=["AI Chat"])


# ─────────────────────────────────────────────
#  Request / Response schemas
# ─────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str        # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


# ─────────────────────────────────────────────
#  System prompts
# ─────────────────────────────────────────────

CLIENT_SYSTEM_PROMPT = """
You are a helpful assistant for clients of this store.
You can ONLY access data belonging to the authenticated client.
You CANNOT access other clients data, admin data, or internal business metrics.

When a client searches for a product and you get a deep_link in the tool result,
always show it as a button like this: [VIEW PRODUCT](deep_link_url)

Be friendly, concise, and helpful.
Always respond in the same language the user writes in (Arabic, French, or English).
"""

ADMIN_SYSTEM_PROMPT = """
You are a business intelligence assistant for the store admin.
You have full access to all business data: sales, inventory, clients, and payments.

Always provide clear summaries, proactively flag issues (low stock, high unpaid bills),
and give actionable insights when relevant.

Be professional and data-driven.
Always respond in the same language the admin writes in (Arabic, French, or English).
"""


# ─────────────────────────────────────────────
#  Client Chat Endpoint
# ─────────────────────────────────────────────

@router.post("/client")
async def client_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    # current_client=Depends(get_current_client),  # ← uncomment when auth ready
):
    # Replace with: client_id = current_client.id
    client_id = 1

    # Define tools as closures — db and client_id are baked in securely
    def get_my_bills() -> dict:
        """Get my bills and their current payment and delivery status."""
        return get_client_bills(db, client_id)

    def get_my_account_summary() -> dict:
        """Get my financial account summary: total amount, amount paid, and remaining balance."""
        return get_client_account_summary(db, client_id)

    def search_products(query: str) -> dict:
        """Search for products available in the store by name.

        Args:
            query: The product name or keyword to search for.
        """
        return search_products_for_client(db, query)

    def get_bill_details(bill_number: str) -> dict:
        """Get the full item breakdown of one of my specific bills.

        Args:
            bill_number: The bill number (e.g. BILL-001).
        """
        return get_bill_details_for_client(db, client_id, bill_number)

    messages = [m.dict() for m in request.history] + [
        {"role": "user", "content": request.message}
    ]

    reply = chat_with_gemini(
        messages=messages,
        tool_functions=[get_my_bills, get_my_account_summary,
                        search_products, get_bill_details],
        system_prompt=CLIENT_SYSTEM_PROMPT,
    )

    return {"reply": reply}


# ─────────────────────────────────────────────
#  Admin Chat Endpoint
# ─────────────────────────────────────────────

@router.post("/admin")
async def admin_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    # current_admin=Depends(get_current_admin),  # ← uncomment when auth ready
):
    # Define tools as closures — db is baked in
    def get_stats() -> dict:
        """Get overall business dashboard stats: total revenue, total bills, unpaid bills count, and low stock count."""
        return get_dashboard_stats(db)

    def list_clients() -> dict:
        """List all active clients with their names and outstanding balances."""
        return get_all_clients_summary(db)

    def low_stock_products() -> dict:
        """Get all products that are at or below their minimum stock level."""
        return get_low_stock_products(db)

    def search_products(query: str) -> dict:
        """Search any product by name, including inactive ones.

        Args:
            query: Product name keyword to search for.
        """
        return search_any_product(db, query)

    def recent_payments() -> dict:
        """Get the most recent payments processed in the store."""
        return get_recent_payments(db)

    def get_bills_with_status() -> dict:
        """Get all bills with payment status and client names. Shows paid and unpaid bills."""
        return get_all_bills_with_status(db)

    messages = [m.dict() for m in request.history] + [
        {"role": "user", "content": request.message}
    ]

    reply = chat_with_gemini(
        messages=messages,
        tool_functions=[get_stats, list_clients, low_stock_products,
                        search_products, recent_payments, get_bills_with_status],
        system_prompt=ADMIN_SYSTEM_PROMPT,
    )

    return {"reply": reply}
