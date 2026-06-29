# utils/tracking.py
#
# Generates short human-readable tracking codes and QR codes.
# Format: AB-XXXX-YY  (prefix + 4 random digits + 2 random uppercase letters)
# Example: AB-4829-KT
#
# The QR code encodes the full public tracking URL so customers can scan
# it directly without needing to type anything.
#
import random
import string
import base64
import io
import os

import qrcode
from qrcode.image.pure import PyPNGImage

# ── Config ────────────────────────────────────────────────────────────────────

# Prefix shown in the code — change to match your brand (e.g. "DZ", "MED", "AB")
CODE_PREFIX = os.getenv("TRACKING_CODE_PREFIX", "AB")

# Base URL of your public storefront — used to build the QR code URL
# e.g. https://yoursite.dz/track?code=AB-4829-KT
STOREFRONT_URL = os.getenv("STOREFRONT_URL", "https://yoursite.dz")


# ── Code generation ───────────────────────────────────────────────────────────


def generate_tracking_code() -> str:
    """
    Generate a short, readable tracking code.
    Format: {PREFIX}-{4 digits}-{2 uppercase letters}
    Example: AB-4829-KT

    Collision probability is negligible for typical COD volumes
    (10,000 * 676 = ~6.7M combinations per prefix).
    The caller (order creation) should verify uniqueness in DB and retry if needed.
    """
    digits = "".join(random.choices(string.digits, k=4))
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    return f"{CODE_PREFIX}-{digits}-{letters}"


# ── QR code generation ────────────────────────────────────────────────────────


def generate_qr_base64(tracking_code: str) -> str:
    """
    Generate a QR code PNG for the given tracking code.
    The QR code encodes the full tracking URL:
      {STOREFRONT_URL}/track?code={tracking_code}

    Returns a base64-encoded PNG string (no data URI prefix).
    The frontend can use it as:
      <img src="data:image/png;base64,{result}" />
    """
    tracking_url = f"{STOREFRONT_URL}/track?code={tracking_code}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(tracking_url)
    qr.make(fit=True)

    # Use pure Python PNG backend — no Pillow required
    img = qr.make_image(image_factory=PyPNGImage)

    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


def generate_tracking_assets(tracking_code: str) -> dict:
    """
    Convenience wrapper — returns both the code and the QR base64.
    """
    return {
        "tracking_code": tracking_code,
        "qr_code_base64": generate_qr_base64(tracking_code),
        "tracking_url": f"{STOREFRONT_URL}/track?code={tracking_code}",
    }
