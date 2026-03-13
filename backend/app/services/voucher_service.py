"""PDF Voucher Generation Pipeline — WeasyPrint based.

Features:
- HTML/CSS template system
- Brand-aware themes
- QR code support
- Localization-ready fields
- Retry-safe rendering
- Persistent storage
"""
from __future__ import annotations

import io
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("voucher.pipeline")

VOUCHER_STORAGE_DIR = os.environ.get("VOUCHER_STORAGE_DIR", "/app/backend/uploads/vouchers")
os.makedirs(VOUCHER_STORAGE_DIR, exist_ok=True)


def _generate_qr_code_base64(data: str) -> str:
    """Generate QR code as base64 PNG string."""
    try:
        import qrcode
        import base64
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")
    except Exception as e:
        logger.warning("QR code generation failed: %s", e)
        return ""


def render_voucher_html(
    booking: dict,
    *,
    brand: dict | None = None,
    locale: str = "tr",
) -> str:
    """Render voucher HTML from booking data with branding."""
    brand = brand or {}
    brand_name = brand.get("name", "Travel Platform")
    brand_color = brand.get("primary_color", "#1a365d")
    brand_logo_url = brand.get("logo_url", "")
    accent_color = brand.get("accent_color", "#e53e3e")

    booking_id = booking.get("booking_id", booking.get("_id", "N/A"))
    confirmation_code = booking.get("confirmation_code", "N/A")
    guest_name = booking.get("guest_name", booking.get("contact", {}).get("name", "Guest"))
    hotel_name = booking.get("hotel_name", booking.get("supplier_name", "N/A"))
    check_in = booking.get("check_in", "N/A")
    check_out = booking.get("check_out", "N/A")
    room_type = booking.get("room_type", "Standard")
    total_price = booking.get("total_price", booking.get("sell_amount", "N/A"))
    currency = booking.get("currency", "EUR")
    special_requests = booking.get("special_requests", "")
    created_at = booking.get("created_at", datetime.now(timezone.utc).isoformat())

    # QR code with booking reference
    qr_data = f"BOOKING:{booking_id}|CONF:{confirmation_code}"
    qr_base64 = _generate_qr_code_base64(qr_data)
    qr_img_tag = f'<img src="data:image/png;base64,{qr_base64}" width="120" height="120" />' if qr_base64 else ""

    logo_tag = f'<img src="{brand_logo_url}" height="40" style="max-height:40px;" />' if brand_logo_url else ""

    # Labels by locale
    labels = {
        "tr": {
            "voucher_title": "Rezervasyon Voucher",
            "booking_ref": "Rezervasyon No",
            "confirmation": "Onay Kodu",
            "guest": "Misafir",
            "hotel": "Otel",
            "check_in": "Giris",
            "check_out": "Cikis",
            "room": "Oda Tipi",
            "total": "Toplam Tutar",
            "special": "Ozel Istekler",
            "generated": "Olusturulma",
            "footer": "Bu belge elektronik olarak olusturulmustur.",
        },
        "en": {
            "voucher_title": "Booking Voucher",
            "booking_ref": "Booking Ref",
            "confirmation": "Confirmation Code",
            "guest": "Guest Name",
            "hotel": "Hotel",
            "check_in": "Check-in",
            "check_out": "Check-out",
            "room": "Room Type",
            "total": "Total Amount",
            "special": "Special Requests",
            "generated": "Generated",
            "footer": "This document was generated electronically.",
        },
    }
    l = labels.get(locale, labels["en"])

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 20px; background: #f7f7f7; color: #333; }}
.voucher {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
.header {{ background: {brand_color}; color: white; padding: 24px 30px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ margin: 0; font-size: 22px; font-weight: 600; }}
.body {{ padding: 30px; }}
.row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
.row:last-child {{ border-bottom: none; }}
.label {{ color: #666; font-size: 13px; font-weight: 500; }}
.value {{ font-weight: 600; font-size: 14px; text-align: right; }}
.qr-section {{ text-align: center; padding: 20px; border-top: 2px dashed #ddd; margin-top: 20px; }}
.footer {{ background: #f8f8f8; padding: 16px 30px; font-size: 11px; color: #999; text-align: center; border-top: 1px solid #eee; }}
.accent {{ color: {accent_color}; }}
.special {{ background: #fff9e6; padding: 12px; border-radius: 4px; margin-top: 10px; font-size: 13px; }}
</style></head>
<body>
<div class="voucher">
  <div class="header">
    <div>
      {logo_tag}
      <h1>{l['voucher_title']}</h1>
    </div>
    <div style="text-align:right;font-size:12px;">
      <div>{brand_name}</div>
      <div>{l['generated']}: {created_at[:10]}</div>
    </div>
  </div>
  <div class="body">
    <div class="row"><span class="label">{l['booking_ref']}</span><span class="value accent">{booking_id}</span></div>
    <div class="row"><span class="label">{l['confirmation']}</span><span class="value">{confirmation_code}</span></div>
    <div class="row"><span class="label">{l['guest']}</span><span class="value">{guest_name}</span></div>
    <div class="row"><span class="label">{l['hotel']}</span><span class="value">{hotel_name}</span></div>
    <div class="row"><span class="label">{l['check_in']}</span><span class="value">{check_in}</span></div>
    <div class="row"><span class="label">{l['check_out']}</span><span class="value">{check_out}</span></div>
    <div class="row"><span class="label">{l['room']}</span><span class="value">{room_type}</span></div>
    <div class="row"><span class="label">{l['total']}</span><span class="value accent">{total_price} {currency}</span></div>
    {"<div class='special'><strong>" + l['special'] + ":</strong> " + special_requests + "</div>" if special_requests else ""}
    <div class="qr-section">
      {qr_img_tag}
      <div style="font-size:11px;color:#999;margin-top:8px;">Scan for booking details</div>
    </div>
  </div>
  <div class="footer">{l['footer']}</div>
</div>
</body></html>"""


def render_pdf(html: str) -> bytes:
    """Render HTML to PDF using WeasyPrint."""
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


async def generate_voucher(
    db,
    org_id: str,
    booking_id: str,
    *,
    brand: dict | None = None,
    locale: str = "tr",
    actor: str = "system",
) -> dict[str, Any]:
    """Generate voucher PDF for a booking. Idempotent — returns existing if already generated."""
    now = datetime.now(timezone.utc).isoformat()

    # Check for existing voucher
    existing = await db.vouchers.find_one(
        {"organization_id": org_id, "booking_id": booking_id, "status": "active"},
        {"_id": 0},
    )
    if existing:
        return existing

    # Get booking data
    from bson import ObjectId
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    except Exception:
        booking = await db.bookings.find_one({"_id": booking_id, "organization_id": org_id})

    if not booking:
        return {"error": "booking_not_found", "booking_id": booking_id}

    booking_data = {
        "booking_id": str(booking.get("_id", booking_id)),
        "confirmation_code": booking.get("confirmation_code", "N/A"),
        "guest_name": booking.get("guest_name", booking.get("contact", {}).get("name", "Guest")),
        "hotel_name": booking.get("hotel_name", booking.get("supplier_name", "N/A")),
        "check_in": str(booking.get("check_in", "N/A")),
        "check_out": str(booking.get("check_out", "N/A")),
        "room_type": booking.get("room_type", "Standard"),
        "total_price": booking.get("sell_amount", booking.get("total_price", 0)),
        "currency": booking.get("currency", "EUR"),
        "special_requests": booking.get("special_requests", ""),
        "created_at": str(booking.get("created_at", now)),
    }

    # Render HTML and PDF
    html = render_voucher_html(booking_data, brand=brand, locale=locale)
    try:
        pdf_bytes = render_pdf(html)
    except Exception as exc:
        logger.error("PDF render failed for booking %s: %s", booking_id, exc)
        return {"error": "pdf_render_failed", "booking_id": booking_id, "detail": str(exc)[:200]}

    # Store PDF
    voucher_id = str(uuid.uuid4())
    filename = f"voucher_{booking_id}_{voucher_id[:8]}.pdf"
    filepath = os.path.join(VOUCHER_STORAGE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    # Save voucher record
    voucher_doc = {
        "voucher_id": voucher_id,
        "organization_id": org_id,
        "booking_id": booking_id,
        "filename": filename,
        "filepath": filepath,
        "size_bytes": len(pdf_bytes),
        "locale": locale,
        "status": "active",
        "generated_by": actor,
        "generated_at": now,
    }
    await db.vouchers.insert_one(voucher_doc)

    return {
        "voucher_id": voucher_id,
        "booking_id": booking_id,
        "filename": filename,
        "size_bytes": len(pdf_bytes),
        "status": "active",
        "generated_at": now,
    }


async def get_voucher_pdf_path(db, org_id: str, booking_id: str) -> str | None:
    """Get the file path for a voucher PDF."""
    doc = await db.vouchers.find_one(
        {"organization_id": org_id, "booking_id": booking_id, "status": "active"},
        {"_id": 0, "filepath": 1},
    )
    if doc and os.path.exists(doc.get("filepath", "")):
        return doc["filepath"]
    return None
