"""Global Tax Handling Service.

Supports:
  - VAT (KDV) calculation
  - Tourism tax
  - Supplier tax included/excluded normalization
  - Booking total breakdown with tax components
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("tax_engine")

# Tax rates by country/region
TAX_RATES = {
    "TR": {"vat_pct": 20.0, "tourism_tax_pct": 2.0, "label": "KDV + Konaklama Vergisi"},
    "AE": {"vat_pct": 5.0, "tourism_tax_pct": 0.0, "label": "VAT"},
    "GB": {"vat_pct": 20.0, "tourism_tax_pct": 0.0, "label": "VAT"},
    "DE": {"vat_pct": 7.0, "tourism_tax_pct": 5.0, "label": "MwSt + Kurtaxe"},
    "FR": {"vat_pct": 10.0, "tourism_tax_pct": 3.0, "label": "TVA + Taxe de Sejour"},
    "IT": {"vat_pct": 10.0, "tourism_tax_pct": 5.0, "label": "IVA + Tassa di Soggiorno"},
    "ES": {"vat_pct": 10.0, "tourism_tax_pct": 2.5, "label": "IVA + Tasa Turistica"},
    "GR": {"vat_pct": 13.0, "tourism_tax_pct": 4.0, "label": "FPA + Tourism Tax"},
    "US": {"vat_pct": 0.0, "tourism_tax_pct": 0.0, "label": "No Federal Tax"},
    "DEFAULT": {"vat_pct": 0.0, "tourism_tax_pct": 0.0, "label": "No Tax"},
}

# Supplier tax inclusion modes
SUPPLIER_TAX_MODES = {
    "ratehawk": "tax_included",
    "tbo": "tax_excluded",
    "paximum": "tax_included",
    "wtatil": "tax_included",
}


def get_tax_rates(country_code: str) -> dict[str, Any]:
    """Get tax rates for a country."""
    return TAX_RATES.get(country_code.upper(), TAX_RATES["DEFAULT"])


def calculate_tax_breakdown(
    base_price: float,
    country_code: str = "TR",
    supplier_code: str = "",
    nights: int = 1,
    rooms: int = 1,
    guests: int = 2,
) -> dict[str, Any]:
    """Calculate tax breakdown for a booking.

    Returns complete price breakdown with tax components.
    """
    rates = get_tax_rates(country_code)
    tax_mode = SUPPLIER_TAX_MODES.get(supplier_code.replace("real_", ""), "tax_included")

    vat_pct = rates["vat_pct"]
    tourism_pct = rates["tourism_tax_pct"]

    if tax_mode == "tax_included":
        # Supplier price already includes taxes - extract them
        vat_amount = base_price * vat_pct / (100 + vat_pct)
        net_price = base_price - vat_amount
        tourism_tax = base_price * tourism_pct / 100
    else:
        # Supplier price is net - add taxes on top
        net_price = base_price
        vat_amount = net_price * vat_pct / 100
        tourism_tax = base_price * tourism_pct / 100

    total_tax = vat_amount + tourism_tax
    gross_price = net_price + total_tax

    return {
        "base_price": round(base_price, 2),
        "net_price": round(net_price, 2),
        "vat_amount": round(vat_amount, 2),
        "vat_pct": vat_pct,
        "tourism_tax": round(tourism_tax, 2),
        "tourism_tax_pct": tourism_pct,
        "total_tax": round(total_tax, 2),
        "gross_price": round(gross_price, 2),
        "tax_mode": tax_mode,
        "tax_label": rates["label"],
        "country_code": country_code.upper(),
        "nights": nights,
        "rooms": rooms,
        "guests": guests,
    }


def normalize_supplier_price(
    supplier_price: float,
    supplier_code: str,
    target_mode: str = "tax_included",
    country_code: str = "TR",
) -> dict[str, Any]:
    """Normalize supplier price to a consistent tax mode.

    Ensures all prices are comparable regardless of supplier tax handling.
    """
    source_mode = SUPPLIER_TAX_MODES.get(supplier_code.replace("real_", ""), "tax_included")
    rates = get_tax_rates(country_code)

    if source_mode == target_mode:
        return {
            "original_price": supplier_price,
            "normalized_price": supplier_price,
            "conversion": "none",
            "tax_mode": target_mode,
        }

    if source_mode == "tax_excluded" and target_mode == "tax_included":
        # Add tax
        vat = supplier_price * rates["vat_pct"] / 100
        normalized = supplier_price + vat
    elif source_mode == "tax_included" and target_mode == "tax_excluded":
        # Remove tax
        vat = supplier_price * rates["vat_pct"] / (100 + rates["vat_pct"])
        normalized = supplier_price - vat
    else:
        normalized = supplier_price

    return {
        "original_price": round(supplier_price, 2),
        "normalized_price": round(normalized, 2),
        "conversion": f"{source_mode} -> {target_mode}",
        "tax_mode": target_mode,
    }


async def get_supported_tax_regions() -> list[dict[str, Any]]:
    """Return all supported tax regions with rates."""
    return [
        {
            "country_code": code,
            "vat_pct": info["vat_pct"],
            "tourism_tax_pct": info["tourism_tax_pct"],
            "label": info["label"],
        }
        for code, info in TAX_RATES.items()
        if code != "DEFAULT"
    ]
