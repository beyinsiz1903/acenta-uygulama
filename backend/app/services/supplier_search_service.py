from __future__ import annotations

from typing import Any, Dict

from fastapi import status

from app.errors import AppError
from app.services.suppliers.paximum_adapter import (
    PaximumAdapter,
    PaximumAuthError,
    PaximumError,
    PaximumRetryableError,
    PaximumValidationError,
    paximum_adapter,
)


async def search_paximum_offers(organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Search Paximum upstream and normalize to internal offer shape.

    Gate responsibilities:
    - Enforce request currency == "TRY"
    - Call upstream /v1/search/hotels via PaximumAdapter
    - Map upstream errors -> 503 SUPPLIER_UPSTREAM_UNAVAILABLE
    - Enforce response currency == "TRY" (otherwise 422 UNSUPPORTED_CURRENCY)
    - Normalize offers to {supplier, currency, search_id, offers:[...]}
    """

    from app.services.currency_guard import ensure_try

    request_currency = payload.get("currency", "TRY")
    ensure_try(request_currency)

    destination = payload.get("destination", {})
    destinations = [destination] if destination else payload.get("destinations", [])
    rooms = payload.get("rooms", [{"adults": 2, "childrenAges": []}])

    try:
        result = await paximum_adapter.search_hotels(
            destinations=destinations,
            rooms=rooms,
            check_in_date=payload.get("checkInDate", ""),
            check_out_date=payload.get("checkOutDate", ""),
            currency=request_currency,
            customer_nationality=payload.get("nationality", "TR"),
            only_best_offers=payload.get("onlyBestOffers", False),
        )
    except PaximumAuthError as exc:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="SUPPLIER_AUTH_FAILED",
            message="Paximum authentication failed.",
            details={"supplier": "paximum", "reason": str(exc)},
        ) from exc
    except (PaximumRetryableError, PaximumError) as exc:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="SUPPLIER_UPSTREAM_UNAVAILABLE",
            message="Paximum supplier service is temporarily unavailable.",
            details={"supplier": "paximum", "reason": str(exc)},
        ) from exc
    except Exception as exc:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="SUPPLIER_UPSTREAM_UNAVAILABLE",
            message="Paximum supplier service is temporarily unavailable.",
            details={"supplier": "paximum", "reason": str(exc)},
        ) from exc

    offers_out = []
    for hotel in result.hotels:
        for offer in hotel.offers:
            offers_out.append(
                {
                    "offer_id": offer.offer_id,
                    "hotel_name": hotel.name,
                    "hotel_id": hotel.hotel_id,
                    "total_amount": float(offer.price.amount),
                    "currency": offer.price.currency,
                    "board": offer.board,
                    "is_available": offer.is_available,
                    "is_special": offer.is_special,
                    "search_id": result.search_id or "",
                    "expires_on": offer.expires_on.isoformat() if offer.expires_on else None,
                    "cancellation_policies": [
                        {
                            "permitted_date": cp.permitted_date.isoformat() if cp.permitted_date else None,
                            "fee_amount": float(cp.fee.amount),
                            "fee_currency": cp.fee.currency,
                        }
                        for cp in offer.cancellation_policies
                    ],
                }
            )

    return {
        "supplier": "paximum",
        "currency": request_currency,
        "search_id": result.search_id or "",
        "hotel_count": len(result.hotels),
        "offer_count": len(offers_out),
        "offers": offers_out,
    }
