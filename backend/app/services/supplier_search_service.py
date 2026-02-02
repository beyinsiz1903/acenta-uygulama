from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, status

from app.services.supplier_warnings import SupplierWarning, map_exception_to_warning, sort_warnings

from app.errors import AppError
from app.services.suppliers.paximum_adapter import paximum_adapter


async def search_paximum_offers(organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Search Paximum upstream and normalize to internal offer shape.

    Gate responsibilities for Sprint 3:
    - Enforce request currency == "TRY"
    - Call upstream /v1/search/hotels via PaximumAdapter
    - Map upstream 5xx/timeout -> 503 SUPPLIER_UPSTREAM_UNAVAILABLE
    - Enforce response currency == "TRY" (otherwise 422 UNSUPPORTED_CURRENCY)
    - Normalize offers to {supplier, currency, search_id, offers:[...]}
    """

    from app.services.currency_guard import ensure_try

    # Request-level currency guard
    ensure_try(payload.get("currency"))

    try:
        resp = await paximum_adapter.search_hotels(payload)
    except Exception as exc:  # Network/timeout errors
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="SUPPLIER_UPSTREAM_UNAVAILABLE",
            message="Paximum supplier service is temporarily unavailable.",
            details={"supplier": "paximum", "reason": str(exc)},
        ) from exc

    # Upstream status mapping
    if resp.status_code >= 500:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="SUPPLIER_UPSTREAM_UNAVAILABLE",
            message="Paximum supplier service is temporarily unavailable.",
            details={"supplier": "paximum", "upstream_status": resp.status_code},
        )

    data = resp.json()

    search_id = data.get("searchId") or ""
    root_currency = (data.get("currency") or payload.get("currency") or "").upper()

    # Response-level currency guard (root)
    from app.services.currency_guard import ensure_try

    ensure_try(root_currency)

    offers_out = []
    for offer in data.get("offers") or []:
        pricing = offer.get("pricing") or {}
        offer_currency = (pricing.get("currency") or root_currency or "").upper()
        ensure_try(offer_currency)

        hotel = offer.get("hotel") or {}
        hotel_name = hotel.get("name") or hotel.get("hotelName") or ""

        offers_out.append(
            {
                "offer_id": offer.get("offerId"),
                "hotel_name": hotel_name,
                "total_amount": float(pricing.get("totalAmount") or 0.0),
                "currency": offer_currency,
                "is_available": True,
                "search_id": search_id,
            }
        )

    return {
        "supplier": "paximum",
        "currency": root_currency,
        "search_id": search_id,
        "offers": offers_out,
    }
