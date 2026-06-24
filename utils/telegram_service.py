# utils/telegram_service.py
"""
Optional Telegram notification for new storefront orders.

Setup (one-time):
1. Message @BotFather on Telegram, /newbot, get your bot token.
2. Add the bot to the chat/group/channel you want alerts in, or just
   message the bot directly from your own account.
3. Get the chat_id: send any message to the bot, then visit
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   and read "chat":{"id": ...} from the response.
4. Set these two env vars (e.g. in your .env):
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   TELEGRAM_CHAT_ID=123456789

If either env var is missing, notifications are silently skipped —
this is intentionally optional and never blocks order creation.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def is_telegram_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_new_order_telegram_alert(order) -> bool:
    """
    Sends a formatted new-order alert to Telegram.
    `order` is an EcommerceOrder SQLAlchemy instance (already committed).
    Returns True if sent successfully, False otherwise (never raises).
    """
    if not is_telegram_configured():
        logger.info(
            "Telegram not configured, skipping notification (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set)"
        )
        return False

    text = (
        f"🛒 Nouvelle commande #{order.id}\n\n"
        f"👤 Client: {order.full_name}\n"
        f"📞 Téléphone: {order.phone_number}\n"
        f"📍 Wilaya: {order.wilaya_name}\n"
        f"🏘 Baladia: {order.baladia_name}\n"
        f"🏠 Adresse: {order.address_details or '-'}\n\n"
        f"📦 Produit: {order.product_name_snapshot}\n"
        f"🔢 Quantité: {order.quantity}\n"
        f"💰 Total: {order.total_price} DA\n"
    )

    url = TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram notification failed for order #{order.id}: {str(e)}")
        return False
