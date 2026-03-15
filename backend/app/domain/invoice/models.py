"""Invoice domain models (Faz 1).

Canonical entities for the invoice engine:
- Invoice
- InvoiceLine
- CustomerBillingProfile
- TaxBreakdown
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    READY_FOR_ISSUE = "ready_for_issue"
    ISSUING = "issuing"
    ISSUED = "issued"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    SYNC_PENDING = "sync_pending"
    SYNCED = "synced"
    SYNC_FAILED = "sync_failed"


class InvoiceType(str, Enum):
    EFATURA = "e_fatura"
    EARSIV = "e_arsiv"
    DRAFT_ONLY = "draft_only"
    ACCOUNTING_ONLY = "accounting_only"


class ProductType(str, Enum):
    HOTEL = "hotel"
    TOUR = "tour"
    FLIGHT = "flight"
    TRANSFER = "transfer"
    ACTIVITY = "activity"


class CustomerType(str, Enum):
    B2B = "b2b"
    B2C = "b2c"


def build_invoice_line(
    description: str,
    quantity: float,
    unit_price: float,
    tax_rate: float = 20.0,
    product_type: str = "hotel",
    line_type: str = "service",
) -> dict[str, Any]:
    """Build a canonical invoice line item."""
    line_total = round(quantity * unit_price, 2)
    tax_amount = round(line_total * tax_rate / 100, 2)
    return {
        "description": description,
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "line_total": line_total,
        "gross_total": round(line_total + tax_amount, 2),
        "product_type": product_type,
        "line_type": line_type,
    }


def build_tax_breakdown(lines: list[dict[str, Any]], currency: str = "TRY") -> dict[str, Any]:
    """Aggregate tax breakdown from invoice lines."""
    subtotal = sum(ln.get("line_total", 0) for ln in lines)
    tax_total = sum(ln.get("tax_amount", 0) for ln in lines)
    grand_total = subtotal + tax_total

    tax_groups: dict[float, float] = {}
    for ln in lines:
        rate = ln.get("tax_rate", 0)
        tax_groups[rate] = tax_groups.get(rate, 0) + ln.get("tax_amount", 0)

    return {
        "subtotal": round(subtotal, 2),
        "tax_total": round(tax_total, 2),
        "grand_total": round(grand_total, 2),
        "currency": currency,
        "tax_groups": [
            {"rate": rate, "amount": round(amt, 2)}
            for rate, amt in sorted(tax_groups.items())
        ],
    }


def build_customer_billing_profile(
    name: str,
    tax_id: str = "",
    tax_office: str = "",
    id_number: str = "",
    customer_type: str = "b2c",
    address: str = "",
    city: str = "",
    country: str = "TR",
    email: str = "",
    phone: str = "",
) -> dict[str, Any]:
    """Build customer billing profile for invoice."""
    return {
        "name": name,
        "tax_id": tax_id,
        "tax_office": tax_office,
        "id_number": id_number,
        "customer_type": customer_type,
        "address": address,
        "city": city,
        "country": country,
        "email": email,
        "phone": phone,
    }


def build_currency_info(
    invoice_currency: str = "TRY",
    booking_currency: str = "TRY",
    exchange_rate: Optional[float] = None,
) -> dict[str, Any]:
    """Build currency info block for invoice."""
    return {
        "invoice_currency": invoice_currency,
        "booking_currency": booking_currency,
        "exchange_rate": exchange_rate or 1.0,
        "same_currency": invoice_currency == booking_currency,
    }
