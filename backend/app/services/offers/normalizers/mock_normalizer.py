from __future__ import annotations

from typing import Any, Dict, List

from app.services.offers.canonical import (
    CanonicalCancellationPolicy,
    CanonicalHotel,
    CanonicalHotelOffer,
    CanonicalMoney,
    CanonicalRoom,
    CanonicalStay,
    make_raw_fingerprint,
)


async def normalize_mock_search_result(payload: Dict[str, Any], supplier_response: Dict[str, Any]) -> List[CanonicalHotelOffer]:
    """Normalize mock supplier search response into canonical hotel offers.

    The current mock response shape is:
    {
        "supplier": "mock_v1",
        "currency": "TRY",
        "items": [
            {"offer_id": ..., "hotel_name": ..., "total_price": ..., "is_available": True},
            ...
        ],
    }
    """

    currency = (supplier_response.get("currency") or "TRY").upper()
    items = supplier_response.get("items") or []

    check_in = str(payload.get("check_in") or "")
    check_out = str(payload.get("check_out") or "")
    guests = int(payload.get("guests") or 1)
    city = str(payload.get("city") or "")

    # Derive simple occupancy: all guests treated as adults for mock
    adults = guests
    children = 0

    from datetime import datetime

    def _parse_date(value: str) -> Optional[datetime]:  # type: ignore[name-defined]
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            return None

    dt_in = _parse_date(check_in)
    dt_out = _parse_date(check_out)
    nights = 1
    if dt_in and dt_out and dt_out > dt_in:
        nights = (dt_out - dt_in).days

    offers: List[CanonicalHotelOffer] = []
    for item in items:
        if not item.get("is_available", True):
            continue

        offer_id = str(item.get("offer_id"))
        hotel_name = str(item.get("hotel_name") or "Mock Hotel")
        total_price = float(item.get("total_price") or 0.0)

        hotel = CanonicalHotel(name=hotel_name, city=city or None)
        stay = CanonicalStay(
            check_in=check_in,
            check_out=check_out,
            nights=nights,
            adults=adults,
            children=children,
        )
        room = CanonicalRoom(room_name=None, board_type=None)
        cancellation_policy = CanonicalCancellationPolicy(refundable=None, deadline=None, raw=None)
        price = CanonicalMoney(amount=total_price, currency=currency)

        raw = {
            "offer_id": offer_id,
            "hotel_name": hotel_name,
            "total_price": total_price,
            "currency": currency,
            "city": city,
        }
        fingerprint = make_raw_fingerprint(raw)

        from uuid import uuid4

        offer_token = str(uuid4())

        offers.append(
            CanonicalHotelOffer(
                offer_token=offer_token,
                supplier_code="mock",
                supplier_offer_id=offer_id,
                product_type="hotel",
                hotel=hotel,
                stay=stay,
                room=room,
                cancellation_policy=cancellation_policy,
                price=price,
                availability_token=None,
                raw_fingerprint=fingerprint,
            )
        )

    return offers
