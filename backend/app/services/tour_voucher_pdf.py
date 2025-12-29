from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

try:  # dateutil is optional but preferred
    from dateutil.parser import isoparse  # type: ignore
except Exception:  # pragma: no cover
    isoparse = None  # type: ignore


def _try_register_fonts() -> tuple[str, str]:
  """Register DejaVu fonts if available; fall back to Helvetica.

  Returns (regular_font_name, bold_font_name).
  """
  try:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")))
    return "DejaVu", "DejaVu-Bold"
  except Exception:  # pragma: no cover
    return "Helvetica", "Helvetica-Bold"


STATUS_MAP_TR: Dict[str, str] = {
  "new": "Yeni",
  "approved": "Onaylandı",
  "rejected": "Reddedildi",
  "cancelled": "İptal",
}


def status_to_tr(raw: Optional[str]) -> str:
  if not raw:
    return "-"
  key = str(raw).lower()
  return STATUS_MAP_TR.get(key, str(raw))


def format_date_ymd_to_tr(value: Optional[str]) -> str:
  """'YYYY-MM-DD' -> 'DD.MM.YYYY'"""
  if not value:
    return "-"
  try:
    dt = datetime.strptime(value[:10], "%Y-%m-%d")
    return dt.strftime("%d.%m.%Y")
  except Exception:  # pragma: no cover
    return str(value)


def format_iso_datetime_to_tr_date(value: Any) -> str:
  """ISO datetime or datetime -> 'DD.MM.YYYY'"""
  if not value:
    return "-"
  try:
    if isinstance(value, datetime):
      return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
      if isoparse is not None:
        dt = isoparse(value)
        return dt.strftime("%d.%m.%Y")
      return value[:10]
    return str(value)
  except Exception:  # pragma: no cover
    return str(value)


def format_iban_display(iban: Optional[str]) -> str:
  iban_s = (iban or "").replace(" ", "").upper()
  if not iban_s:
    return "-"
  return " ".join(iban_s[i : i + 4] for i in range(0, len(iban_s), 4))


def draw_wrapped_text(
  c: canvas.Canvas,
  text: str,
  x: float,
  y: float,
  font_name: str,
  font_size: int,
  max_width: float,
  line_h: float,
) -> float:
  """Draw text with simple word wrap, returning new y position."""
  if not text:
    return y
  c.setFont(font_name, font_size)
  lines = simpleSplit(str(text), font_name, font_size, max_width)
  for line in lines:
    c.drawString(x, y, line)
    y -= line_h
  return y


def render_tour_voucher_pdf(model: Dict[str, Any]) -> bytes:
  """Render a simple one-page tour voucher PDF from normalized model.

  Model fields used (all optional, defaulting to '-'): agency_name, reference_code,
  request_id, guest_* fields, tour_title, desired_date, pax, status, payment{}.
  """
  width, height = A4
  x = 40
  y = height - 50
  line_h = 16
  max_width = 510  # safe width with 40/40 margins

  font_regular, font_bold = _try_register_fonts()

  buf = BytesIO()
  try:
    c = canvas.Canvas(buf, pagesize=A4)

    # Header
    c.setFont(font_bold, 16)
    c.drawString(x, y, "Tur Voucher / Rezervasyon Özeti")
    y -= 2 * line_h

    agency_name = model.get("agency_name") or "-"
    c.setFont(font_bold, 11)
    c.drawString(x, y, f"Acenta: {agency_name}")
    y -= line_h

    reference_code = model.get("reference_code") or "-"
    request_id = model.get("request_id") or "-"
    c.setFont(font_regular, 10)
    c.drawString(x, y, f"Voucher No: {reference_code}   Talep ID: {request_id}")
    y -= 2 * line_h

    # Guest block
    c.setFont(font_bold, 11)
    c.drawString(x, y, "Misafir Bilgileri")
    y -= line_h

    c.setFont(font_regular, 10)
    c.drawString(x, y, f"Ad Soyad: {model.get('guest_full_name') or '-'}")
    y -= line_h
    c.drawString(x, y, f"Telefon: {model.get('guest_phone') or '-'}")
    y -= line_h
    c.drawString(x, y, f"E-posta: {model.get('guest_email') or '-'}")
    y -= 2 * line_h

    # Tour block
    c.setFont(font_bold, 11)
    c.drawString(x, y, "Tur Bilgileri")
    y -= line_h

    tour_title = model.get("tour_title") or "-"
    y = draw_wrapped_text(c, f"Tur: {tour_title}", x, y, font_regular, 10, max_width, line_h)

    desired_date_tr = format_date_ymd_to_tr(model.get("desired_date"))
    c.setFont(font_regular, 10)
    c.drawString(x, y, f"Tarih: {desired_date_tr}")
    y -= line_h

    c.drawString(x, y, f"Kişi Sayısı: {model.get('pax') or '-'}")
    y -= line_h

    c.drawString(x, y, f"Durum: {status_to_tr(model.get('status'))}")
    y -= 2 * line_h

    # Offline payment block
    c.setFont(font_bold, 11)
    c.drawString(x, y, "Offline Ödeme Talimatı (IBAN)")
    y -= line_h

    payment = model.get("payment") or {}
    snap = (payment.get("iban_snapshot") or {}) if isinstance(payment, dict) else {}

    account_name = snap.get("account_name") or "-"
    bank_name = snap.get("bank_name") or "-"
    iban_disp = format_iban_display(snap.get("iban"))
    swift = snap.get("swift") or "—"
    currency = payment.get("currency") or snap.get("currency") or "TRY"

    c.setFont(font_regular, 10)
    c.drawString(x, y, f"Hesap Sahibi: {account_name}")
    y -= line_h
    c.drawString(x, y, f"Banka Adı: {bank_name}")
    y -= line_h
    c.drawString(x, y, f"IBAN: {iban_disp}")
    y -= line_h
    c.drawString(x, y, f"SWIFT: {swift}")
    y -= line_h

    amount = payment.get("amount")
    if amount is None:
      amount_str = "-"
    else:
      try:
        amount_str = f"{float(amount):.2f} {currency}"
      except Exception:  # pragma: no cover
        amount_str = f"{amount} {currency}"

    due_at_tr = format_iso_datetime_to_tr_date(payment.get("due_at"))
    c.drawString(x, y, f"Tutar: {amount_str}")
    y -= line_h
    c.drawString(x, y, f"Son Ödeme Tarihi: {due_at_tr}")
    y -= 2 * line_h

    # Payment note suggestion
    c.setFont(font_bold, 11)
    c.drawString(x, y, "Ödeme Açıklaması Önerisi")
    y -= line_h

    note_template = snap.get("note_template") or "Rezervasyon: {reference_code}"
    note_filled = str(note_template).replace("{reference_code}", str(reference_code))
    y = draw_wrapped_text(c, note_filled, x, y, font_regular, 10, max_width, line_h)

    # Footer
    c.setFont(font_regular, 9)
    c.drawString(x, 40, "Bu belge elektronik olarak oluşturulmuştur. İmzaya gerek yoktur.")

    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
  finally:
    buf.close()

  return pdf_bytes
