from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Register DejaVu fonts for proper Turkish character support
try:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
except Exception:
    # Fallback to built-in fonts if DejaVu is not available
    pass

from app.services.payments_offline import get_payment_instructions, _compute_payable_amount


def _fmt_tr_date(value: Any) -> str:
    """Accepts ISO string/datetime; returns DD.MM.YYYY or '—'"""
    if not value:
        return "—"
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif isinstance(value, datetime):
            dt = value
        else:
            return "—"
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return "—"


def _safe(val: Any) -> str:
    if val is None:
        return "—"
    s = str(val).strip()
    return s if s else "—"


async def ensure_payment_reference(organization_id: str, booking: Dict[str, Any]) -> Dict[str, Any]:
    """Guarantee booking.payment.reference_code exists via payment instructions.

    Uses existing offline payment flow to create payment+reference if missing.
    Returns (possibly updated) booking dict (callers should reload from DB if they need fresh data).
    """
    payment = booking.get("payment") or {}
    if payment.get("reference_code"):
        return booking

    # This will ensure payment exists + reference is created if booking payable; DB is updated there.
    await get_payment_instructions(organization_id=organization_id, booking=booking)
    return booking


def build_voucher_model(
    booking: Dict[str, Any],
    org: Dict[str, Any],
    hotel: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payment = booking.get("payment") or {}
    guest = booking.get("guest") or {}
    stay = booking.get("stay") or {}
    occ = booking.get("occupancy") or {}
    rs = booking.get("rate_snapshot") or {}
    rs_price = (rs.get("price") or {}) if isinstance(rs, dict) else {}

    issuer_name = _safe((hotel or {}).get("name")) if hotel else _safe(org.get("display_name"))
    if issuer_name == "—":
        issuer_name = _safe(org.get("display_name"))

    hotel_address = _safe((hotel or {}).get("address")) if hotel else "—"
    hotel_phone = _safe((hotel or {}).get("phone")) if hotel else "—"
    hotel_email = _safe((hotel or {}).get("email")) if hotel else "—"

    guest_full_name = guest.get("full_name")
    if not guest_full_name:
        fn = (guest.get("first_name") or "").strip()
        ln = (guest.get("last_name") or "").strip()
        guest_full_name = (f"{fn} {ln}").strip() if (fn or ln) else "—"
    guest_full_name = _safe(guest_full_name)

    room_type = _safe(rs.get("room_type_label") if isinstance(rs, dict) else None)
    if room_type == "—":
        room_type = _safe(booking.get("room_type_name"))

    board = _safe(rs.get("board_code") if isinstance(rs, dict) else None)

    check_in = _fmt_tr_date(stay.get("check_in"))
    check_out = _fmt_tr_date(stay.get("check_out"))

    adults = occ.get("adults")
    children = occ.get("children")
    pax_str = "—"
    try:
        if adults is not None or children is not None:
            a = int(adults or 0)
            c = int(children or 0)
            pax_str = f"{a} Yetişkin, {c} Çocuk"
    except Exception:
        pass

    amount = payment.get("amount")
    currency = payment.get("currency") or booking.get("currency") or rs_price.get("currency") or "TRY"
    if amount is None:
        amt, cur = _compute_payable_amount(booking)
        amount, currency = amt, cur or currency

    reference = payment.get("reference_code") or "—"

    pay_status = payment.get("status")
    payment_status_label = "Ödendi" if pay_status == "paid" else "Ödenmedi"

    return {
        "reference": reference,
        "booking_id": _safe(booking.get("_id") or booking.get("booking_id")),
        "issuer_name": issuer_name,
        "hotel_address": hotel_address,
        "hotel_phone": hotel_phone,
        "hotel_email": hotel_email,
        "guest_full_name": guest_full_name,
        "room_type": room_type,
        "board": board,
        "check_in": check_in,
        "check_out": check_out,
        "pax": pax_str,
        "amount": amount,
        "currency": currency,
        "payment_status_label": payment_status_label,
    }


def render_voucher_pdf_reportlab(model: Dict[str, Any]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    x = 40
    y = height - 50
    line_h = 16

    # Title
    c.setFont("DejaVu-Bold", 16)
    c.drawString(x, y, "Konaklama Voucher'ı")
    y -= 2 * line_h

    # Issuer block
    c.setFont("DejaVu-Bold", 11)
    c.drawString(x, y, "Düzenleyen (Issuer)")
    y -= line_h

    c.setFont("DejaVu", 10)
    c.drawString(x, y, f"Otel/Kurum: {model['issuer_name']}")
    y -= line_h
    c.drawString(x, y, f"Adres: {model['hotel_address']}")
    y -= line_h
    c.drawString(x, y, f"Telefon: {model['hotel_phone']}   E-posta: {model['hotel_email']}")
    y -= 2 * line_h

    # Booking block
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Rezervasyon Bilgileri")
    y -= line_h

    c.setFont("DejaVu", 10)
    c.drawString(x, y, f"Voucher No: {model['reference']}")
    y -= line_h
    c.drawString(x, y, f"Rezervasyon No: {model['booking_id']}")
    y -= line_h
    c.drawString(x, y, f"Tarih: {model['check_in']} - {model['check_out']}")
    y -= 2 * line_h

    # Stay details
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Konaklama Detayları")
    y -= line_h

    c.setFont("DejaVu", 10)
    c.drawString(x, y, f"Misafir: {model['guest_full_name']}")
    y -= line_h
    c.drawString(x, y, f"Oda Tipi: {model['room_type']}    Pansiyon: {model['board']}")
    y -= line_h
    c.drawString(x, y, f"Kişi: {model['pax']}")
    y -= 2 * line_h

    # Payment
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Ödeme")
    y -= line_h

    c.setFont("DejaVu", 10)
    c.drawString(x, y, f"Tutar: {_safe(model['amount'])} {model['currency']}")
    y -= line_h
    c.drawString(x, y, f"Ödeme Durumu: {model['payment_status_label']}")
    y -= 3 * line_h

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(x, 40, "Bu belge elektronik olarak oluşturulmuştur.")
    c.showPage()
    c.save()

    return buf.getvalue()


async def generate_voucher_pdf(
    organization_id: str,
    booking: Dict[str, Any],
    org: Dict[str, Any],
    hotel: Optional[Dict[str, Any]],
) -> Tuple[bytes, str]:
    # Ensure payment reference exists
    await ensure_payment_reference(organization_id, booking)

    # Build model and render PDF (booking may be slightly stale but reference is guaranteed in DB)
    model = build_voucher_model(booking, org, hotel)
    pdf_bytes = render_voucher_pdf_reportlab(model)
    filename = f"voucher-{model['reference']}.pdf"
    return pdf_bytes, filename
