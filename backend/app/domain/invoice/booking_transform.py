"""Booking → Invoice Transformation (Faz 1).

Maps confirmed bookings into invoice-ready financial documents.
Full support: hotel, tour
Placeholder support: flight, transfer, activity
"""
from __future__ import annotations

from typing import Any

from app.domain.invoice.models import (
    build_currency_info,
    build_invoice_line,
    build_tax_breakdown,
)
from app.services.tax_engine import calculate_tax_breakdown


def transform_booking_to_invoice_lines(booking: dict[str, Any]) -> list[dict[str, Any]]:
    """Transform a booking into invoice line items.

    Supports hotel and tour with full detail.
    Other product types get a single-line summary.
    """
    product_type = _detect_product_type(booking)
    lines: list[dict[str, Any]] = []

    if product_type == "hotel":
        lines = _transform_hotel(booking)
    elif product_type == "tour":
        lines = _transform_tour(booking)
    else:
        lines = _transform_generic(booking, product_type)

    return lines


def build_invoice_from_booking(booking: dict[str, Any], customer_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a complete invoice payload from a booking.

    Returns a dict ready to be persisted as an invoice document.
    """
    lines = transform_booking_to_invoice_lines(booking)
    currency = booking.get("currency") or "TRY"
    tax_info = build_tax_breakdown(lines, currency)
    currency_info = build_currency_info(
        invoice_currency=currency,
        booking_currency=booking.get("currency", "TRY"),
    )

    booking_id = str(booking.get("id") or booking.get("_id") or "")
    product_type = _detect_product_type(booking)

    return {
        "booking_id": booking_id,
        "product_type": product_type,
        "lines": lines,
        "totals": tax_info,
        "currency_info": currency_info,
        "customer": customer_profile or {},
        "booking_ref": booking.get("booking_ref") or "",
        "hotel_name": booking.get("hotel_name") or "",
        "guest_name": booking.get("guest_name") or booking.get("customer_name") or "",
        "stay": booking.get("stay") or {},
    }


def _detect_product_type(booking: dict[str, Any]) -> str:
    """Detect product type from booking data."""
    pt = booking.get("product_type", "")
    if pt:
        return pt
    if booking.get("hotel_id") or booking.get("hotel_name"):
        return "hotel"
    if booking.get("tour_id"):
        return "tour"
    return "hotel"


def _transform_hotel(booking: dict[str, Any]) -> list[dict[str, Any]]:
    """Transform hotel booking into invoice lines."""
    lines = []
    stay = booking.get("stay") or {}
    check_in = stay.get("check_in", "")
    check_out = stay.get("check_out", "")
    hotel_name = booking.get("hotel_name") or "Otel"
    nights = _calc_nights(check_in, check_out)
    country = booking.get("country_code") or "TR"

    amount = float(booking.get("amount") or booking.get("gross_amount") or 0)
    tax_info = calculate_tax_breakdown(amount, country_code=country, supplier_code=booking.get("supplier_id", ""))

    per_night = round(tax_info["net_price"] / max(nights, 1), 2)

    lines.append(build_invoice_line(
        description=f"{hotel_name} - Konaklama ({check_in} / {check_out}, {nights} gece)",
        quantity=nights,
        unit_price=per_night,
        tax_rate=tax_info["vat_pct"],
        product_type="hotel",
        line_type="accommodation",
    ))

    if tax_info.get("tourism_tax", 0) > 0:
        lines.append(build_invoice_line(
            description="Konaklama Vergisi",
            quantity=1,
            unit_price=tax_info["tourism_tax"],
            tax_rate=0,
            product_type="hotel",
            line_type="tourism_tax",
        ))

    markup = float(booking.get("agency_markup") or booking.get("commission_amount") or 0)
    if markup > 0:
        lines.append(build_invoice_line(
            description="Hizmet Bedeli",
            quantity=1,
            unit_price=markup,
            tax_rate=tax_info["vat_pct"],
            product_type="hotel",
            line_type="agency_fee",
        ))

    return lines


def _transform_tour(booking: dict[str, Any]) -> list[dict[str, Any]]:
    """Transform tour booking into invoice lines."""
    lines = []
    tour_name = booking.get("tour_name") or booking.get("hotel_name") or "Tur"
    amount = float(booking.get("amount") or booking.get("gross_amount") or 0)
    country = booking.get("country_code") or "TR"
    tax_info = calculate_tax_breakdown(amount, country_code=country)
    guests = int(booking.get("occupancy", {}).get("adults", 1) or 1)

    per_person = round(tax_info["net_price"] / max(guests, 1), 2)

    lines.append(build_invoice_line(
        description=f"{tour_name} - Tur Paketi ({guests} kisi)",
        quantity=guests,
        unit_price=per_person,
        tax_rate=tax_info["vat_pct"],
        product_type="tour",
        line_type="package",
    ))

    markup = float(booking.get("agency_markup") or booking.get("commission_amount") or 0)
    if markup > 0:
        lines.append(build_invoice_line(
            description="Hizmet Bedeli",
            quantity=1,
            unit_price=markup,
            tax_rate=tax_info["vat_pct"],
            product_type="tour",
            line_type="service_fee",
        ))

    return lines


def _transform_generic(booking: dict[str, Any], product_type: str) -> list[dict[str, Any]]:
    """Generic single-line invoice for unsupported product types."""
    amount = float(booking.get("amount") or booking.get("gross_amount") or 0)
    country = booking.get("country_code") or "TR"
    tax_info = calculate_tax_breakdown(amount, country_code=country)

    type_labels = {
        "flight": "Ucus",
        "transfer": "Transfer",
        "activity": "Aktivite",
    }
    label = type_labels.get(product_type, product_type.capitalize())

    return [build_invoice_line(
        description=f"{label} Hizmeti",
        quantity=1,
        unit_price=tax_info["net_price"],
        tax_rate=tax_info["vat_pct"],
        product_type=product_type,
        line_type="service",
    )]


def _calc_nights(check_in: str, check_out: str) -> int:
    """Calculate number of nights from date strings."""
    if not check_in or not check_out:
        return 1
    try:
        from datetime import datetime
        ci = datetime.fromisoformat(check_in.replace("Z", "+00:00")) if "T" in check_in else datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.fromisoformat(check_out.replace("Z", "+00:00")) if "T" in check_out else datetime.strptime(check_out, "%Y-%m-%d")
        delta = (co - ci).days
        return max(delta, 1)
    except Exception:
        return 1
