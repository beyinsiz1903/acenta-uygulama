"""
Comprehensive Corporate Voucher HTML Template Generator

Generates professional, print-ready voucher documents for both
hotel and tour reservations.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def _safe(val, default="-"):
    """Safely get string representation of a value."""
    if val is None or val == "" or val == []:
        return default
    return str(val)


def _format_money(amount, currency="TRY"):
    """Format money with thousands separator."""
    if amount is None:
        return "-"
    try:
        amt = float(amount)
        formatted = f"{amt:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} {currency or 'TRY'}"
    except (ValueError, TypeError):
        return f"{amount} {currency or 'TRY'}"


def _format_date(date_str):
    """Format date nicely."""
    if not date_str:
        return "-"
    s = str(date_str)[:10]
    try:
        parts = s.split("-")
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
    except Exception:
        pass
    return s


def _status_label(status):
    """Get Turkish status label."""
    labels = {
        "pending": "Beklemede",
        "confirmed": "Onaylandı",
        "CONFIRMED": "Onaylandı",
        "paid": "Ödendi",
        "PAID": "Ödendi",
        "cancelled": "İptal Edildi",
        "CANCELLED": "İptal Edildi",
        "completed": "Tamamlandı",
        "COMPLETED": "Tamamlandı",
        "VOUCHERED": "Voucher Kesildi",
    }
    return labels.get(status, _safe(status))


def _status_color(status):
    """Get status badge color."""
    s = (status or "").lower()
    if s in ("confirmed", "paid", "completed", "vouchered"):
        return "#059669", "#ecfdf5", "#059669"
    elif s in ("pending",):
        return "#d97706", "#fffbeb", "#d97706"
    elif s in ("cancelled",):
        return "#dc2626", "#fef2f2", "#dc2626"
    return "#6b7280", "#f3f4f6", "#6b7280"


def _payment_status_label(status):
    """Get Turkish payment status label."""
    labels = {
        "unpaid": "Ödenmedi",
        "partial": "Kısmi Ödendi",
        "paid": "Tamamı Ödendi",
    }
    return labels.get(status, _safe(status))


def _build_price_items_html(price_items, currency):
    """Build price items table rows."""
    if not price_items:
        return '<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:16px 0;">Fiyat detayı bulunmamaktadır.</td></tr>'

    rows = []
    for idx, item in enumerate(price_items):
        bg = '#f9fafb' if idx % 2 == 0 else '#ffffff'
        rows.append(
            f'<tr style="background:{bg}">'
            f'<td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;">{_format_date(item.get("date"))}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;text-align:right;">{_format_money(item.get("unit_price"), currency)}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;text-align:center;">{_safe(item.get("pax"), "1")}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;text-align:right;font-weight:600;">{_format_money(item.get("total"), currency)}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _build_itinerary_html(itinerary):
    """Build tour itinerary section."""
    if not itinerary:
        return ""

    rows = []
    for idx, day in enumerate(itinerary):
        day_num = day.get("day") or (idx + 1)
        title = _safe(day.get("title"), "")
        desc = _safe(day.get("description"), "")
        rows.append(
            f'<div style="display:flex;gap:16px;padding:12px 0;border-bottom:1px solid #f3f4f6;">'
            f'  <div style="min-width:48px;height:48px;background:linear-gradient(135deg,#0e7490,#0891b2);color:#fff;'
            f'border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;">Gün {day_num}</div>'
            f'  <div style="flex:1;">'
            f'    <div style="font-weight:600;font-size:14px;color:#111827;margin-bottom:4px;">{title}</div>'
            f'    <div style="font-size:13px;color:#6b7280;line-height:1.5;">{desc}</div>'
            f'  </div>'
            f'</div>'
        )
    return "\n".join(rows)


def _build_includes_excludes_html(includes, excludes):
    """Build includes/excludes section."""
    if not includes and not excludes:
        return ""

    html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:12px;">'

    # Includes
    html += '<div>'
    html += '<div style="font-weight:600;font-size:13px;color:#059669;margin-bottom:8px;display:flex;align-items:center;gap:6px;">'
    html += '<span style="font-size:16px;">&#10003;</span> Fiyata Dahil Hizmetler</div>'
    if includes:
        for item in includes:
            text = item if isinstance(item, str) else (item.get("text") or item.get("name") or str(item))
            html += '<div style="font-size:13px;color:#374151;padding:4px 0;padding-left:22px;position:relative;">'
            html += f'<span style="position:absolute;left:0;color:#059669;">&#8226;</span>{text}</div>'
    else:
        html += '<div style="font-size:13px;color:#9ca3af;">Bilgi bulunmamaktadır.</div>'
    html += '</div>'

    # Excludes
    html += '<div>'
    html += '<div style="font-weight:600;font-size:13px;color:#dc2626;margin-bottom:8px;display:flex;align-items:center;gap:6px;">'
    html += '<span style="font-size:16px;">&#10007;</span> Fiyata Dahil Olmayan Hizmetler</div>'
    if excludes:
        for item in excludes:
            text = item if isinstance(item, str) else (item.get("text") or item.get("name") or str(item))
            html += '<div style="font-size:13px;color:#374151;padding:4px 0;padding-left:22px;position:relative;">'
            html += f'<span style="position:absolute;left:0;color:#dc2626;">&#8226;</span>{text}</div>'
    else:
        html += '<div style="font-size:13px;color:#9ca3af;">Bilgi bulunmamaktadır.</div>'
    html += '</div>'

    html += '</div>'
    return html


def generate_reservation_voucher_html(
    reservation: dict[str, Any],
    product: Optional[dict[str, Any]] = None,
    customer: Optional[dict[str, Any]] = None,
    organization: Optional[dict[str, Any]] = None,
    tour: Optional[dict[str, Any]] = None,
    tour_reservation: Optional[dict[str, Any]] = None,
    rate_plan: Optional[dict[str, Any]] = None,
    agency: Optional[dict[str, Any]] = None,
) -> str:
    """Generate comprehensive corporate voucher HTML."""

    res = reservation or {}
    prod = product or {}
    cust = customer or {}
    org = organization or {}
    tour_data = tour or {}
    tour_res = tour_reservation or {}
    rp = rate_plan or {}
    ag = agency or {}

    # Determine reservation type
    is_tour = bool(res.get("tour_id") or res.get("source") == "tour" or tour_data)
    product_type = "tour" if is_tour else _safe(prod.get("type"), "hotel")

    # Organization info
    org_name = _safe(org.get("name"), "Acenta")
    org_settings = org.get("settings") or {}

    # Reservation basics
    voucher_no = _safe(res.get("voucher_no"), res.get("pnr", "-"))
    pnr = _safe(res.get("pnr"))
    status = res.get("status") or "pending"
    status_label = _status_label(status)
    status_text_color, status_bg_color, status_border_color = _status_color(status)
    created_at = res.get("created_at")
    created_at_str = "-"
    if created_at:
        if hasattr(created_at, "strftime"):
            created_at_str = created_at.strftime("%d.%m.%Y %H:%M")
        else:
            created_at_str = _format_date(str(created_at))

    # Guest / Customer info
    guest_name = _safe(
        res.get("customer_name") or res.get("guest_name") or cust.get("name"),
        "-"
    )
    guest_email = _safe(
        res.get("customer_email") or res.get("guest_email") or cust.get("email"),
        "-"
    )
    guest_phone = _safe(
        res.get("customer_phone") or res.get("guest_phone") or cust.get("phone"),
        "-"
    )

    # Pax info
    pax_info = ""
    if res.get("pax") and isinstance(res["pax"], dict):
        adults = res["pax"].get("adults", 0)
        children = res["pax"].get("children", 0)
        pax_info = f"{adults} Yetişkin"
        if children:
            pax_info += f", {children} Çocuk"
    elif res.get("pax"):
        pax_info = f"{res['pax']} Kişi"
    else:
        pax_info = "-"

    # Product / Hotel / Tour info
    product_name = ""
    product_location = ""
    product_description = ""
    product_type_label = ""

    if is_tour:
        product_name = _safe(
            res.get("product_title") or tour_data.get("name") or tour_res.get("tour_name"),
            "-"
        )
        product_location = _safe(
            tour_data.get("destination") or tour_res.get("tour_destination") or res.get("destination"),
            "-"
        )
        product_description = _safe(tour_data.get("description"), "")
        product_type_label = "Tur"
        duration_text = _safe(tour_data.get("duration"), "")
        departure_city = _safe(tour_data.get("departure_city"), "")
        max_participants = tour_data.get("max_participants")
    else:
        product_name = _safe(
            prod.get("title") or prod.get("name", {}).get("tr") if isinstance(prod.get("name"), dict) else prod.get("name") or prod.get("title"),
            "-"
        )
        if isinstance(prod.get("name"), dict):
            product_name = _safe(prod["name"].get("tr") or prod["name"].get("en"), product_name)
        product_location = ""
        if prod.get("location"):
            loc = prod["location"]
            if isinstance(loc, dict):
                product_location = f"{loc.get('city', '')} / {loc.get('country', '')}".strip(" /")
            else:
                product_location = str(loc)
        product_description = _safe(prod.get("description"), "")
        product_type_label = "Otel" if product_type == "hotel" else _safe(product_type).capitalize()

    # Dates
    start_date = _format_date(res.get("start_date") or res.get("check_in"))
    end_date = _format_date(res.get("end_date") or res.get("check_out"))
    if is_tour:
        travel_date = _format_date(tour_res.get("travel_date") or res.get("start_date") or res.get("check_in"))

    # Calculate nights/days
    night_count = ""
    try:
        sd = str(res.get("start_date") or res.get("check_in") or "")[:10]
        ed = str(res.get("end_date") or res.get("check_out") or "")[:10]
        if sd and ed and sd != ed:
            from datetime import date as dt_date
            d1 = dt_date.fromisoformat(sd)
            d2 = dt_date.fromisoformat(ed)
            diff = (d2 - d1).days
            if diff > 0:
                if is_tour:
                    night_count = f"{diff + 1} Gün / {diff} Gece"
                else:
                    night_count = f"{diff} Gece"
    except Exception:
        pass

    # Price info
    currency = _safe(res.get("currency"), "TRY")
    total_price = res.get("total_price") or 0
    paid_amount = res.get("paid_amount") or 0
    due_amount = round(float(total_price or 0) - float(paid_amount or 0), 2)
    discount_amount = res.get("discount_amount") or 0
    commission_amount = res.get("commission_amount") or 0
    price_items = res.get("price_items") or []

    # Payment status
    payment_status = res.get("payment_status", "")
    if not payment_status:
        if float(paid_amount or 0) >= float(total_price or 0) and float(total_price or 0) > 0:
            payment_status = "paid"
        elif float(paid_amount or 0) > 0:
            payment_status = "partial"
        else:
            payment_status = "unpaid"

    # Tour specific pricing from tour_reservation
    tour_pricing = tour_res.get("pricing") or {}
    if is_tour and tour_pricing:
        base_price_per_person = tour_pricing.get("base_price", 0)
        participants = tour_pricing.get("participants", 0)
        subtotal = tour_pricing.get("subtotal", 0)
        taxes = tour_pricing.get("taxes", 0)
        total_price = tour_pricing.get("total", total_price)
        currency = tour_pricing.get("currency", currency)

    # Board type / room info (hotel)
    room_type = _safe(rp.get("name") or rp.get("code"), "")
    board_type = _safe(rp.get("board"), "")
    board_labels = {
        "BB": "Oda Kahvaltı (BB)",
        "HB": "Yarım Pansiyon (HB)",
        "FB": "Tam Pansiyon (FB)",
        "AI": "Her Şey Dahil (AI)",
        "RO": "Sadece Oda (RO)",
        "UAI": "Ultra Her Şey Dahil (UAI)",
    }
    board_label = board_labels.get(board_type, board_type)

    # Tour itinerary, includes, excludes
    itinerary = tour_data.get("itinerary") or []
    includes = tour_data.get("includes") or []
    excludes = tour_data.get("excludes") or []
    highlights = tour_data.get("highlights") or []

    # Agency info
    agency_name = _safe(ag.get("name"), "")
    channel = _safe(res.get("channel"), "direct")

    # Now
    now_str = datetime.utcnow().strftime("%d.%m.%Y %H:%M")

    # ===== BUILD HTML =====
    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Voucher - {voucher_no}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
      background: #f1f5f9;
      padding: 20px;
      color: #1e293b;
      line-height: 1.6;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }}
    .voucher-container {{
      max-width: 960px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }}

    /* Header */
    .voucher-header {{
      background: linear-gradient(135deg, #0c4a6e 0%, #0e7490 50%, #06b6d4 100%);
      padding: 32px 40px;
      color: #ffffff;
      position: relative;
      overflow: hidden;
    }}
    .voucher-header::before {{
      content: '';
      position: absolute;
      top: -50%;
      right: -20%;
      width: 400px;
      height: 400px;
      background: rgba(255,255,255,0.05);
      border-radius: 50%;
    }}
    .voucher-header::after {{
      content: '';
      position: absolute;
      bottom: -60%;
      left: -10%;
      width: 300px;
      height: 300px;
      background: rgba(255,255,255,0.03);
      border-radius: 50%;
    }}
    .header-content {{
      position: relative;
      z-index: 1;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 20px;
    }}
    .header-left {{
      flex: 1;
      min-width: 200px;
    }}
    .header-right {{
      text-align: right;
      min-width: 200px;
    }}
    .company-name {{
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.5px;
      margin-bottom: 4px;
    }}
    .voucher-title {{
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 3px;
      opacity: 0.85;
      margin-bottom: 2px;
    }}
    .voucher-subtitle {{
      font-size: 12px;
      opacity: 0.7;
    }}
    .header-badge {{
      display: inline-block;
      background: rgba(255,255,255,0.2);
      backdrop-filter: blur(4px);
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 10px;
      padding: 8px 16px;
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .header-badge strong {{
      font-size: 15px;
      display: block;
      margin-top: 2px;
    }}

    /* Ribbon */
    .status-ribbon {{
      padding: 10px 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      border-bottom: 1px solid #e2e8f0;
      background: #f8fafc;
    }}
    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 16px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      background: {status_bg_color};
      color: {status_text_color};
      border: 1px solid {status_border_color}20;
    }}
    .status-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: {status_text_color};
    }}
    .ribbon-info {{
      font-size: 12px;
      color: #64748b;
    }}

    /* Body */
    .voucher-body {{
      padding: 32px 40px;
    }}

    /* Section */
    .section {{
      margin-bottom: 28px;
    }}
    .section-title {{
      font-size: 14px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: #0e7490;
      margin-bottom: 14px;
      padding-bottom: 8px;
      border-bottom: 2px solid #e0f2fe;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .section-icon {{
      width: 24px;
      height: 24px;
      background: linear-gradient(135deg, #0e7490, #06b6d4);
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 12px;
      flex-shrink: 0;
    }}

    /* Info Grid */
    .info-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;
    }}
    .info-item {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 12px 16px;
    }}
    .info-label {{
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #94a3b8;
      margin-bottom: 4px;
    }}
    .info-value {{
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
      word-break: break-word;
    }}
    .info-value.highlight {{
      color: #0e7490;
      font-size: 16px;
    }}

    /* Table */
    .price-table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      overflow: hidden;
    }}
    .price-table thead {{
      background: linear-gradient(135deg, #0c4a6e, #0e7490);
    }}
    .price-table thead th {{
      padding: 12px 16px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #ffffff;
      text-align: left;
    }}
    .price-table thead th:nth-child(2),
    .price-table thead th:nth-child(4) {{
      text-align: right;
    }}
    .price-table thead th:nth-child(3) {{
      text-align: center;
    }}
    .price-table tfoot {{
      background: #f0f9ff;
    }}
    .price-table tfoot td {{
      padding: 14px 16px;
      font-weight: 700;
      font-size: 14px;
      border-top: 2px solid #0e7490;
    }}

    /* Summary Box */
    .summary-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 16px;
    }}
    .summary-box {{
      background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
      border: 1px solid #bae6fd;
      border-radius: 12px;
      padding: 16px 20px;
      text-align: center;
    }}
    .summary-box.total {{
      background: linear-gradient(135deg, #0c4a6e, #0e7490);
      border: none;
      color: #ffffff;
    }}
    .summary-box .summary-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      opacity: 0.7;
      margin-bottom: 4px;
    }}
    .summary-box .summary-value {{
      font-size: 20px;
      font-weight: 700;
    }}
    .summary-box.total .summary-label {{
      color: rgba(255,255,255,0.8);
    }}
    .summary-box.total .summary-value {{
      color: #ffffff;
    }}

    /* Policy Box */
    .policy-box {{
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: 12px;
      padding: 20px 24px;
    }}
    .policy-box.terms {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
    }}
    .policy-title {{
      font-size: 13px;
      font-weight: 700;
      color: #92400e;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .policy-box.terms .policy-title {{
      color: #475569;
    }}
    .policy-item {{
      font-size: 12px;
      color: #78350f;
      padding: 3px 0;
      padding-left: 16px;
      position: relative;
    }}
    .policy-box.terms .policy-item {{
      color: #64748b;
    }}
    .policy-item::before {{
      content: '\\2022';
      position: absolute;
      left: 0;
      color: #d97706;
    }}
    .policy-box.terms .policy-item::before {{
      color: #94a3b8;
    }}

    /* Tour sections */
    .itinerary-section {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 20px 24px;
    }}
    .highlights-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 10px;
      margin-top: 8px;
    }}
    .highlight-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #374151;
      padding: 8px 12px;
      background: #ecfdf5;
      border-radius: 8px;
      border: 1px solid #a7f3d0;
    }}
    .highlight-icon {{
      color: #059669;
      font-size: 14px;
      flex-shrink: 0;
    }}

    /* Footer */
    .voucher-footer {{
      border-top: 1px solid #e2e8f0;
      padding: 20px 40px;
      background: #f8fafc;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .footer-left {{
      font-size: 11px;
      color: #94a3b8;
      line-height: 1.6;
    }}
    .footer-right {{
      display: flex;
      gap: 10px;
    }}

    /* Watermark */
    .watermark {{
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) rotate(-30deg);
      font-size: 120px;
      font-weight: 900;
      color: rgba(14, 116, 144, 0.03);
      pointer-events: none;
      z-index: 0;
      white-space: nowrap;
    }}

    /* Divider */
    .divider {{
      border: none;
      border-top: 1px dashed #cbd5e1;
      margin: 24px 0;
    }}

    /* Print */
    .no-print {{ }}
    .print-btn {{
      background: linear-gradient(135deg, #0e7490, #06b6d4);
      color: #fff;
      border: none;
      border-radius: 10px;
      padding: 10px 20px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.5px;
      transition: all 0.2s;
    }}
    .print-btn:hover {{
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(14, 116, 144, 0.3);
    }}
    .download-btn {{
      background: #ffffff;
      color: #0e7490;
      border: 2px solid #0e7490;
      border-radius: 10px;
      padding: 8px 18px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      transition: all 0.2s;
    }}
    .download-btn:hover {{
      background: #f0f9ff;
    }}

    @media print {{
      .no-print {{ display: none !important; }}
      body {{ background: #fff; padding: 0; margin: 0; }}
      .voucher-container {{ box-shadow: none; border-radius: 0; }}
      .voucher-header {{ border-radius: 0; }}
      .watermark {{ display: none; }}
    }}

    @media (max-width: 640px) {{
      .voucher-header {{ padding: 24px 20px; }}
      .voucher-body {{ padding: 20px; }}
      .voucher-footer {{ padding: 16px 20px; }}
      .header-content {{ flex-direction: column; }}
      .header-right {{ text-align: left; }}
      .info-grid {{ grid-template-columns: 1fr; }}
      .summary-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="watermark">VOUCHER</div>

  <div class="voucher-container">

    <!-- ===== HEADER ===== -->
    <div class="voucher-header">
      <div class="header-content">
        <div class="header-left">
          <div class="company-name">{org_name}</div>
          <div class="voucher-title">Rezervasyon Voucher</div>
          <div class="voucher-subtitle">Booking Confirmation Voucher</div>
        </div>
        <div class="header-right">
          <div class="header-badge">
            <span style="font-size:11px;opacity:0.8;">VOUCHER NO</span>
            <strong>{voucher_no}</strong>
          </div>
          <br />
          <div class="header-badge" style="margin-top:8px;">
            <span style="font-size:11px;opacity:0.8;">PNR</span>
            <strong>{pnr}</strong>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== STATUS RIBBON ===== -->
    <div class="status-ribbon">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
        <span class="status-badge">
          <span class="status-dot"></span>
          {status_label}
        </span>
        <span style="font-size:12px;color:#64748b;">
          {'&#127968; Tur Rezervasyonu' if is_tour else '&#127968; Otel Rezervasyonu'}
        </span>
      </div>
      <div class="ribbon-info">
        Oluşturulma: {created_at_str}
      </div>
    </div>

    <div class="voucher-body">
"""

    # ===== PRODUCT / HOTEL / TOUR INFO =====
    html += f"""
      <!-- ===== ÜRÜN BİLGİLERİ ===== -->
      <div class="section">
        <div class="section-title">
          <div class="section-icon">{'&#9992;' if is_tour else '&#127968;'}</div>
          {'Tur Bilgileri' if is_tour else 'Otel / Konaklama Bilgileri'}
        </div>
        <div class="info-grid">
          <div class="info-item" style="grid-column:span 2;">
            <div class="info-label">{'Tur Adı' if is_tour else 'Otel / Ürün Adı'}</div>
            <div class="info-value highlight">{product_name}</div>
          </div>
"""

    if product_location and product_location != "-":
        html += f"""
          <div class="info-item">
            <div class="info-label">{'Destinasyon' if is_tour else 'Konum'}</div>
            <div class="info-value">{product_location}</div>
          </div>
"""

    html += f"""
          <div class="info-item">
            <div class="info-label">Tür</div>
            <div class="info-value">{product_type_label}</div>
          </div>
"""

    # Tour specific info
    if is_tour:
        if tour_data.get("duration"):
            html += f"""
          <div class="info-item">
            <div class="info-label">Süre</div>
            <div class="info-value">{_safe(tour_data.get("duration"))}</div>
          </div>
"""
        if tour_data.get("departure_city"):
            html += f"""
          <div class="info-item">
            <div class="info-label">Kalkış Şehri</div>
            <div class="info-value">{_safe(tour_data.get("departure_city"))}</div>
          </div>
"""
        if tour_data.get("max_participants"):
            html += f"""
          <div class="info-item">
            <div class="info-label">Maks. Katılımcı</div>
            <div class="info-value">{tour_data.get("max_participants")} Kişi</div>
          </div>
"""
    else:
        # Hotel specific info
        if board_label:
            html += f"""
          <div class="info-item">
            <div class="info-label">Pansiyon Tipi</div>
            <div class="info-value">{board_label}</div>
          </div>
"""
        if room_type:
            html += f"""
          <div class="info-item">
            <div class="info-label">Oda / Plan</div>
            <div class="info-value">{room_type}</div>
          </div>
"""

    html += """
        </div>
      </div>
"""

    # Product description
    if product_description and product_description != "-":
        html += f"""
      <div class="section" style="margin-top:-12px;margin-bottom:24px;">
        <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:14px 18px;font-size:13px;color:#334155;line-height:1.7;">
          {product_description[:500]}
        </div>
      </div>
"""

    # ===== GUEST INFO =====
    html += f"""
      <!-- ===== MİSAFİR BİLGİLERİ ===== -->
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#128100;</div>
          Misafir Bilgileri
        </div>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">Ad Soyad</div>
            <div class="info-value">{guest_name}</div>
          </div>
          <div class="info-item">
            <div class="info-label">E-posta</div>
            <div class="info-value">{guest_email}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Telefon</div>
            <div class="info-value">{guest_phone}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Kişi Sayısı</div>
            <div class="info-value">{pax_info}</div>
          </div>
        </div>
      </div>
"""

    # ===== DATE INFO =====
    html += f"""
      <!-- ===== TARİH BİLGİLERİ ===== -->
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#128197;</div>
          {'Seyahat Tarihi' if is_tour else 'Konaklama Tarihleri'}
        </div>
        <div class="info-grid">
"""

    if is_tour:
        html += f"""
          <div class="info-item" style="grid-column:span 2;">
            <div class="info-label">Hareket Tarihi</div>
            <div class="info-value highlight">{travel_date if is_tour else start_date}</div>
          </div>
"""
    else:
        html += f"""
          <div class="info-item">
            <div class="info-label">Giriş Tarihi (Check-in)</div>
            <div class="info-value highlight">{start_date}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Çıkış Tarihi (Check-out)</div>
            <div class="info-value highlight">{end_date}</div>
          </div>
"""

    if night_count:
        html += f"""
          <div class="info-item">
            <div class="info-label">Süre</div>
            <div class="info-value">{night_count}</div>
          </div>
"""

    if channel and channel != "-" and channel != "direct":
        html += f"""
          <div class="info-item">
            <div class="info-label">Kanal</div>
            <div class="info-value">{channel}</div>
          </div>
"""

    if agency_name:
        html += f"""
          <div class="info-item">
            <div class="info-label">Acente</div>
            <div class="info-value">{agency_name}</div>
          </div>
"""

    html += """
        </div>
      </div>
"""

    # ===== HIGHLIGHTS (Tour) =====
    if is_tour and highlights:
        html += """
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#11088;</div>
          Tur Öne Çıkanlar
        </div>
        <div class="highlights-grid">
"""
        for h in highlights:
            text = h if isinstance(h, str) else (h.get("text") or str(h))
            html += f'          <div class="highlight-item"><span class="highlight-icon">&#10003;</span> {text}</div>\n'
        html += """
        </div>
      </div>
"""

    # ===== ITINERARY (Tour) =====
    if is_tour and itinerary:
        itinerary_html = _build_itinerary_html(itinerary)
        html += f"""
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#128204;</div>
          Tur Programı
        </div>
        <div class="itinerary-section">
          {itinerary_html}
        </div>
      </div>
"""

    # ===== INCLUDES/EXCLUDES (Tour) =====
    if is_tour and (includes or excludes):
        inc_exc_html = _build_includes_excludes_html(includes, excludes)
        html += f"""
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#128221;</div>
          Dahil ve Hariç Hizmetler
        </div>
        {inc_exc_html}
      </div>
"""

    # ===== PRICE BREAKDOWN =====
    price_items_html = _build_price_items_html(price_items, currency)
    html += """
      <!-- ===== ÖDEME DETAYLARI ===== -->
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#128176;</div>
          Ödeme Detayları
        </div>
"""

    # If tour with pricing breakdown
    if is_tour and tour_pricing:
        html += f"""
        <div class="info-grid" style="margin-bottom:16px;">
          <div class="info-item">
            <div class="info-label">Kişi Başı Fiyat</div>
            <div class="info-value">{_format_money(tour_pricing.get('base_price'), currency)}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Katılımcı Sayısı</div>
            <div class="info-value">{tour_pricing.get('participants', '-')} Kişi</div>
          </div>
          <div class="info-item">
            <div class="info-label">Ara Toplam</div>
            <div class="info-value">{_format_money(tour_pricing.get('subtotal'), currency)}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Vergiler</div>
            <div class="info-value">{_format_money(tour_pricing.get('taxes'), currency)}</div>
          </div>
        </div>
"""
    elif price_items:
        html += f"""
        <table class="price-table">
          <thead>
            <tr>
              <th>Tarih</th>
              <th style="text-align:right">Birim Fiyat</th>
              <th style="text-align:center">Kişi</th>
              <th style="text-align:right">Toplam</th>
            </tr>
          </thead>
          <tbody>
            {price_items_html}
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" style="text-align:right;padding-right:16px;">Genel Toplam</td>
              <td style="text-align:right;padding-right:16px;">{_format_money(total_price, currency)}</td>
            </tr>
          </tfoot>
        </table>
"""

    # Payment Summary boxes
    html += f"""
        <div class="summary-grid">
          <div class="summary-box total">
            <div class="summary-label">TOPLAM TUTAR</div>
            <div class="summary-value">{_format_money(total_price, currency)}</div>
          </div>
          <div class="summary-box">
            <div class="summary-label">ÖDENEN TUTAR</div>
            <div class="summary-value" style="color:#059669;">{_format_money(paid_amount, currency)}</div>
          </div>
"""

    if float(due_amount) > 0:
        html += f"""
          <div class="summary-box" style="background:linear-gradient(135deg,#fef2f2,#fee2e2);border-color:#fecaca;">
            <div class="summary-label" style="color:#991b1b;">KALAN TUTAR</div>
            <div class="summary-value" style="color:#dc2626;">{_format_money(due_amount, currency)}</div>
          </div>
"""

    if float(discount_amount) > 0:
        html += f"""
          <div class="summary-box" style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-color:#a7f3d0;">
            <div class="summary-label" style="color:#065f46;">İNDİRİM</div>
            <div class="summary-value" style="color:#059669;">{_format_money(discount_amount, currency)}</div>
          </div>
"""

    html += f"""
        </div>

        <div style="margin-top:12px;text-align:right;">
          <span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#64748b;background:#f1f5f9;padding:6px 14px;border-radius:8px;">
            Ödeme Durumu: <strong style="color:{'#059669' if payment_status == 'paid' else '#d97706' if payment_status == 'partial' else '#dc2626'}">{_payment_status_label(payment_status)}</strong>
          </span>
        </div>
      </div>

      <hr class="divider" />
"""

    # ===== CANCELLATION POLICY =====
    html += """
      <!-- ===== İPTAL POLİTİKASI ===== -->
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#9888;</div>
          İptal ve Değişiklik Politikası
        </div>
        <div class="policy-box">
          <div class="policy-title">
            &#9888;&#65039; Lütfen aşağıdaki iptal koşullarını dikkatlice okuyunuz
          </div>
          <div class="policy-item">Rezervasyon tarihinden 14 gün veya daha fazla süre önce yapılan iptallerde herhangi bir ücret alınmaz.</div>
          <div class="policy-item">Rezervasyon tarihinden 7-14 gün önce yapılan iptallerde toplam tutarın %30'u iptal ücreti olarak tahsil edilir.</div>
          <div class="policy-item">Rezervasyon tarihinden 3-7 gün önce yapılan iptallerde toplam tutarın %50'si iptal ücreti olarak tahsil edilir.</div>
          <div class="policy-item">Rezervasyon tarihinden 3 günden az süre kala yapılan iptallerde veya giriş yapılmaması (no-show) halinde toplam tutarın %100'ü tahsil edilir.</div>
          <div class="policy-item">Tarih değişikliği talepleri, müsaitlik durumuna bağlı olarak en az 7 gün öncesinden yapılmalıdır.</div>
          <div class="policy-item">Grup rezervasyonlarında özel iptal koşulları geçerli olabilir.</div>
        </div>
      </div>
"""

    # ===== TERMS & CONDITIONS =====
    html += f"""
      <!-- ===== ŞARTLAR VE KOŞULLAR ===== -->
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#128203;</div>
          Genel Şartlar ve Koşullar
        </div>
        <div class="policy-box terms">
          <div class="policy-title">
            &#128203; Önemli Bilgiler
          </div>
          <div class="policy-item">Bu voucher, yukarıda belirtilen hizmetler için geçerlidir ve başkasına devredilemez.</div>
          <div class="policy-item">{'Otele giriş sırasında bu voucher belgesinin (basılı veya dijital) ibrazı zorunludur.' if not is_tour else 'Tur hareket noktasında bu voucher belgesinin (basılı veya dijital) ibrazı zorunludur.'}</div>
          <div class="policy-item">Voucher üzerinde belirtilen tarih ve saatlere uyulması misafirimizin sorumluluğundadır.</div>
          <div class="policy-item">{'Check-in saati 14:00, check-out saati 12:00\'dir (otelin politikasına göre değişebilir).' if not is_tour else 'Tur hareket saati, tur programında belirtilen saattir. Hareket saatinden en az 15 dakika önce buluşma noktasında hazır bulunmanız gerekmektedir.'}</div>
          <div class="policy-item">Fiyatlara KDV dahildir (aksi belirtilmedikçe).</div>
          <div class="policy-item">Mücbir sebepler (doğal afet, savaş, salgın vb.) durumunda şirketimiz hizmet koşullarında değişiklik yapma hakkını saklı tutar.</div>
          <div class="policy-item">Ekstra hizmetler (minibar, oda servisi, ekstra turlar vb.) bu voucher kapsamında değildir ve ayrıca faturalandırılır.</div>
          <div class="policy-item">Herhangi bir sorun veya talep için aşağıdaki iletişim bilgilerini kullanabilirsiniz.</div>
        </div>
      </div>

      <!-- ===== İLETİŞİM BİLGİLERİ ===== -->
      <div class="section">
        <div class="section-title">
          <div class="section-icon">&#128222;</div>
          İletişim ve Acil Durum
        </div>
        <div class="info-grid">
          <div class="info-item" style="grid-column:span 2;">
            <div class="info-label">Kurum</div>
            <div class="info-value">{org_name}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Destek E-posta</div>
            <div class="info-value">destek@acenta.com</div>
          </div>
          <div class="info-item">
            <div class="info-label">Acil Durum Hattı</div>
            <div class="info-value">+90 (212) 000 00 00</div>
          </div>
        </div>
      </div>

    </div>
    <!-- end voucher-body -->

    <!-- ===== FOOTER ===== -->
    <div class="voucher-footer">
      <div class="footer-left">
        <div>Bu belge <strong>{org_name}</strong> tarafından oluşturulmuştur.</div>
        <div>Belge No: {voucher_no} &nbsp;|&nbsp; PNR: {pnr} &nbsp;|&nbsp; Oluşturulma: {now_str} (UTC)</div>
        <div style="margin-top:4px;font-size:10px;color:#cbd5e1;">
          Bu voucher yasal bir belge niteliği taşımamaktadır. Bilgilendirme ve referans amaçlıdır.
        </div>
      </div>
      <div class="footer-right no-print">
        <button onclick="window.print()" class="print-btn">&#128424; Yazdır / Print</button>
      </div>
    </div>

  </div>
  <!-- end voucher-container -->

</body>
</html>"""

    return html


def generate_b2b_voucher_html(
    view: dict[str, Any],
    organization: Optional[dict[str, Any]] = None,
) -> str:
    """Generate comprehensive B2B booking voucher HTML."""

    org = organization or {}
    org_name = _safe(org.get("name"), "Acenta")

    hotel = _safe(view.get("hotel_name"), "-")
    guest = _safe(view.get("guest_name"), "-")
    guest_email = _safe(view.get("guest_email"), "-")
    guest_phone = _safe(view.get("guest_phone"), "-")
    check_in = _format_date(view.get("check_in_date"))
    check_out = _format_date(view.get("check_out_date"))
    room = _safe(view.get("room_type"), "-")
    board = _safe(view.get("board_type"), "-")
    total = view.get("total_amount")
    currency = _safe(view.get("currency"), "")
    status_tr = _safe(view.get("status_tr") or view.get("status"), "-")
    status_en = _safe(view.get("status_en"), "-")
    nights = view.get("nights")
    destination = _safe(view.get("destination"), "-")
    agency_name = _safe(view.get("agency_name"), "-")
    code = _safe(view.get("code") or view.get("id"), "-")
    adults = view.get("adults") or 0
    children = view.get("children") or 0
    special_requests = _safe(view.get("special_requests"), "")
    created_at = view.get("created_at") or ""
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    created_at_str = _format_date(str(created_at)[:10]) if created_at else "-"

    total_str = _format_money(total, currency)

    board_labels = {
        "BB": "Oda Kahvaltı (BB)",
        "HB": "Yarım Pansiyon (HB)",
        "FB": "Tam Pansiyon (FB)",
        "AI": "Her Şey Dahil (AI)",
        "RO": "Sadece Oda (RO)",
        "UAI": "Ultra Her Şey Dahil (UAI)",
    }
    board_label = board_labels.get(board, board)

    pax_str = f"{adults} Yetişkin"
    if children:
        pax_str += f", {children} Çocuk"

    status_color, status_bg, _ = _status_color(status_tr)
    now_str = datetime.utcnow().strftime("%d.%m.%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Booking Voucher - {code}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
      background: #f1f5f9;
      padding: 20px;
      color: #1e293b;
      line-height: 1.6;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }}
    .voucher {{ max-width: 960px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
    .header {{ background: linear-gradient(135deg, #0c4a6e 0%, #0e7490 50%, #06b6d4 100%); padding: 32px 40px; color: #fff; }}
    .header-flex {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }}
    .company {{ font-size: 24px; font-weight: 700; }}
    .doc-type {{ font-size: 14px; text-transform: uppercase; letter-spacing: 3px; opacity: 0.85; }}
    .badge-box {{ background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); border-radius: 10px; padding: 8px 16px; font-size: 13px; }}
    .badge-box strong {{ font-size: 15px; display: block; margin-top: 2px; }}
    .status-bar {{ background: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 10px 40px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
    .status-pill {{ padding: 6px 16px; border-radius: 999px; font-size: 13px; font-weight: 600; background: {status_bg}; color: {status_color}; }}
    .body {{ padding: 32px 40px; }}
    .sec {{ margin-bottom: 24px; }}
    .sec-title {{ font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #0e7490; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #e0f2fe; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }}
    .cell {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; }}
    .cell-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 4px; }}
    .cell-value {{ font-size: 14px; font-weight: 600; color: #1e293b; }}
    .cell-value.accent {{ color: #0e7490; font-size: 16px; }}
    .total-box {{ background: linear-gradient(135deg, #0c4a6e, #0e7490); border-radius: 12px; padding: 20px; text-align: center; color: #fff; }}
    .total-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; }}
    .total-val {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
    .policy {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 18px 22px; margin-bottom: 24px; }}
    .policy h4 {{ font-size: 13px; font-weight: 700; color: #92400e; margin-bottom: 8px; }}
    .policy li {{ font-size: 12px; color: #78350f; margin-left: 16px; padding: 2px 0; }}
    .terms {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px 22px; }}
    .terms h4 {{ font-size: 13px; font-weight: 700; color: #475569; margin-bottom: 8px; }}
    .terms li {{ font-size: 12px; color: #64748b; margin-left: 16px; padding: 2px 0; }}
    .footer {{ border-top: 1px solid #e2e8f0; padding: 18px 40px; background: #f8fafc; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }}
    .footer-text {{ font-size: 11px; color: #94a3b8; }}
    .btn {{ background: linear-gradient(135deg, #0e7490, #06b6d4); color: #fff; border: none; border-radius: 10px; padding: 10px 20px; cursor: pointer; font-size: 13px; font-weight: 600; }}
    @media print {{ .no-print {{ display: none !important; }} body {{ background: #fff; padding: 0; }} .voucher {{ box-shadow: none; border-radius: 0; }} }}
    @media (max-width: 640px) {{ .header,.body,.footer,.status-bar {{ padding-left: 20px; padding-right: 20px; }} .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="voucher">
    <div class="header">
      <div class="header-flex">
        <div>
          <div class="company">{org_name}</div>
          <div class="doc-type">Rezervasyon Voucher / Booking Voucher</div>
        </div>
        <div style="text-align:right">
          <div class="badge-box"><span style="font-size:11px;opacity:0.8;">REF</span><strong>{code}</strong></div>
        </div>
      </div>
    </div>

    <div class="status-bar">
      <span class="status-pill">{status_tr} / {status_en}</span>
      <span style="font-size:12px;color:#64748b;">Oluşturulma: {created_at_str}</span>
    </div>

    <div class="body">
      <div class="sec">
        <div class="sec-title">&#127968; Otel Bilgileri</div>
        <div class="grid">
          <div class="cell" style="grid-column:span 2;"><div class="cell-label">Otel</div><div class="cell-value accent">{hotel}</div></div>
          <div class="cell"><div class="cell-label">Destinasyon</div><div class="cell-value">{destination}</div></div>
          <div class="cell"><div class="cell-label">Oda Tipi</div><div class="cell-value">{room}</div></div>
          <div class="cell"><div class="cell-label">Pansiyon</div><div class="cell-value">{board_label}</div></div>
        </div>
      </div>

      <div class="sec">
        <div class="sec-title">&#128100; Misafir Bilgileri</div>
        <div class="grid">
          <div class="cell"><div class="cell-label">Ad Soyad</div><div class="cell-value">{guest}</div></div>
          <div class="cell"><div class="cell-label">E-posta</div><div class="cell-value">{guest_email}</div></div>
          <div class="cell"><div class="cell-label">Telefon</div><div class="cell-value">{guest_phone}</div></div>
          <div class="cell"><div class="cell-label">Kişi Sayısı</div><div class="cell-value">{pax_str}</div></div>
        </div>
      </div>

      <div class="sec">
        <div class="sec-title">&#128197; Konaklama Tarihleri</div>
        <div class="grid">
          <div class="cell"><div class="cell-label">Check-in</div><div class="cell-value accent">{check_in}</div></div>
          <div class="cell"><div class="cell-label">Check-out</div><div class="cell-value accent">{check_out}</div></div>
          <div class="cell"><div class="cell-label">Gece</div><div class="cell-value">{nights if nights else '-'} Gece</div></div>
          {f'<div class="cell"><div class="cell-label">Acente</div><div class="cell-value">{agency_name}</div></div>' if agency_name != '-' else ''}
        </div>
      </div>

      {f'<div class="sec"><div class="sec-title">&#128172; Özel İstekler</div><div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:14px 18px;font-size:13px;color:#334155;">{special_requests}</div></div>' if special_requests and special_requests != '-' else ''}

      <div class="sec">
        <div class="sec-title">&#128176; Ödeme Bilgileri</div>
        <div class="total-box">
          <div class="total-label">TOPLAM TUTAR / TOTAL AMOUNT</div>
          <div class="total-val">{total_str}</div>
        </div>
      </div>

      <div class="policy">
        <h4>&#9888;&#65039; İptal Politikası / Cancellation Policy</h4>
        <ul>
          <li>14 gün ve üzeri öncesinde yapılan iptallerde ücret alınmaz.</li>
          <li>7-14 gün öncesinde: toplam tutarın %30'u tahsil edilir.</li>
          <li>3-7 gün öncesinde: toplam tutarın %50'si tahsil edilir.</li>
          <li>3 günden az / no-show: toplam tutarın %100'ü tahsil edilir.</li>
        </ul>
      </div>

      <div class="terms">
        <h4>&#128203; Genel Şartlar / Terms &amp; Conditions</h4>
        <ul>
          <li>Bu voucher belirtilen hizmetler için geçerlidir ve devredilemez.</li>
          <li>Otele giriş sırasında bu belgenin ibrazı zorunludur.</li>
          <li>Check-in: 14:00 / Check-out: 12:00 (otele göre değişebilir).</li>
          <li>Ekstra hizmetler bu voucher kapsamında değildir.</li>
          <li>Mücbir sebepler durumunda değişiklik hakkı saklıdır.</li>
        </ul>
      </div>
    </div>

    <div class="footer">
      <div class="footer-text">
        <div>{org_name} tarafından oluşturulmuştur. | Ref: {code} | {now_str} UTC</div>
        <div style="margin-top:2px;font-size:10px;">Bu voucher bilgilendirme amaçlıdır, yasal belge niteliği taşımaz.</div>
      </div>
      <div class="no-print">
        <button onclick="window.print()" class="btn">&#128424; Yazdır</button>
      </div>
    </div>
  </div>
</body>
</html>"""
