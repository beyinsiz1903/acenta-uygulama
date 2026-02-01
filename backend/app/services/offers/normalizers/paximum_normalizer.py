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


async def normalize_paximum_search_result(payload: Dict[str, Any], supplier_response: Dict[str, Any]) -> List[CanonicalHotelOffer]:
    """Normalize Paximum search response into canonical hotel offers.

    Expected upstream shape (simplified):
    {
        "searchId": str,
        "currency": "TRY",
        "offers": [
            {
                "offerId": str,
                "pricing": {"totalAmount": float, "currency": "TRY"},
                "hotel": {"name": str, "city": str | None, "country": str | None},
                ...
            },
            ...
        ],
    }
    """

    root_currency = (supplier_response.get("currency") or payload.get("currency") or "TRY").upper()
    offers_in = supplier_response.get("offers") or []

    check_in = str(payload.get("checkInDate") or "")
    check_out = str(payload.get("checkOutDate") or "")

    rooms = payload.get("rooms") or []
    # Very naive occupancy: sum adults/children across rooms
    adults = 0
    children = 0
    for r in rooms:
        adults += int(r.get("adult") or 0)
        children += int(r.get("child") or 0)

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
    for offer in offers_in:
        pricing = offer.get("pricing") or {}
        offer_currency = (pricing.get("currency") or root_currency).upper()
        total_amount = float(pricing.get("totalAmount") or 0.0)

        hotel_doc = offer.get("hotel") or {}
        hotel_name = hotel_doc.get("name") or hotel_doc.get("hotelName") or "Hotel"
        city = hotel_doc.get("city") or None
        country = hotel_doc.get("country") or None

        hotel = CanonicalHotel(name=hotel_name, city=city, country=country)
        stay = CanonicalStay(
            check_in=check_in,
            check_out=check_out,
            nights=nights,
            adults=adults,
            children=children,
        )
        room = CanonicalRoom(room_name=None, board_type=None)

        cancellation_policy = CanonicalCancellationPolicy(refundable=None, deadline=None, raw=None)
        price = CanonicalMoney(amount=total_amount, currency=offer_currency)

        supplier_offer_id = str(offer.get("offerId"))

        raw = {
            "offerId": supplier_offer_id,
            "hotel": hotel_doc,
            "pricing": pricing,
            "currency": offer_currency,
        }
        fingerprint = make_raw_fingerprint(raw)

        from uuid import uuid4

        offer_token = str(uuid4())

        offers.append(
            CanonicalHotelOffer(
                offer_token=offer_token,
                supplier_code="paximum",
                supplier_offer_id=supplier_offer_id,
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
