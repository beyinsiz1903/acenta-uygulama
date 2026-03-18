from __future__ import annotations

from decimal import Decimal
from typing import Any

from .paximum_models import (
    CancellationPolicy,
    Hotel,
    Money,
    Offer,
    PaximumBooking,
    Room,
    SearchResult,
    Traveller,
    parse_dt,
)


def _money(value: dict[str, Any] | None) -> Money | None:
    if not value:
        return None
    amount = value.get("amount", 0)
    currency = value.get("currency") or value.get("code") or "EUR"
    return Money(amount=Decimal(str(amount)), currency=currency)


def _traveller(item: dict[str, Any]) -> Traveller:
    return Traveller(
        type=(item.get("type") or "").lower(),
        age=item.get("age"),
        nationality=item.get("nationality"),
        traveller_no=item.get("travellerNo"),
        title=item.get("title"),
        name=item.get("name"),
        surname=item.get("surname"),
        is_lead=item.get("isLead"),
        email=item.get("email"),
        phone=item.get("phone"),
        mobile=item.get("mobile"),
    )


def _room(item: dict[str, Any]) -> Room:
    return Room(
        room_id=item.get("id") or item.get("roomId") or "",
        room_type=item.get("type") or "",
        room_type_id=item.get("typeId"),
        travellers=[_traveller(x) for x in item.get("travellers", [])],
        price=_money(item.get("price")),
        promotions=item.get("promotions", []),
    )


def _cancellation_policies(items: list[dict[str, Any]] | None) -> list[CancellationPolicy]:
    result: list[CancellationPolicy] = []
    for item in items or []:
        permitted = item.get("permittedDate") or item.get("afterDate")
        fee = _money(item.get("fee"))
        if fee:
            result.append(
                CancellationPolicy(
                    permitted_date=parse_dt(permitted),
                    fee=fee,
                )
            )
    return result


def map_offer(item: dict[str, Any], search_id: str | None = None) -> Offer:
    return Offer(
        offer_id=item.get("id") or "",
        search_id=search_id,
        hotel_id=str(item.get("hotelId") or ""),
        expires_on=parse_dt(item.get("expiresOn")),
        board=item.get("board"),
        board_id=item.get("boardId"),
        board_categories=item.get("boardCategories", []),
        rooms=[_room(x) for x in item.get("rooms", [])],
        price=_money(item.get("price")) or Money(amount=Decimal("0"), currency="EUR"),
        minimum_sale_price=_money(item.get("minimumSalePrice")),
        is_b2c_price=bool(item.get("isB2CPrice", False)),
        is_special=bool(item.get("isSpecial", False)),
        is_available=bool(item.get("isAvailable", False)),
        cancellation_policies=_cancellation_policies(item.get("cancellationPolicies")),
        restrictions=item.get("restrictions", []),
        warnings=item.get("warnings", []),
        notes=item.get("notes", []),
        supplements=item.get("supplements", []),
        raw=item,
    )


def map_hotel(item: dict[str, Any], search_id: str | None = None) -> Hotel:
    city = item.get("city") or {}
    country = item.get("country") or {}
    geolocation = item.get("geolocation") or item.get("geoLocation") or {}
    offers = [map_offer(x, search_id=search_id) for x in item.get("offers", [])]

    return Hotel(
        hotel_id=str(item.get("id") or ""),
        name=item.get("name") or "",
        description=item.get("description"),
        city_id=str(city.get("id")) if city.get("id") is not None else None,
        city_name=city.get("name"),
        country_id=str(country.get("id")) if country.get("id") is not None else None,
        country_name=country.get("name"),
        stars=float(item["stars"]) if item.get("stars") is not None else None,
        rating=float(item["rating"]) if item.get("rating") is not None else None,
        review_url=item.get("reviewUrl"),
        photos=item.get("photos", []) or ([item["thumbnail"]] if item.get("thumbnail") else []),
        themes=item.get("themes", []),
        facilities=item.get("facilities", []),
        content=item.get("content", []),
        address=item.get("address", {}),
        geolocation=geolocation,
        offers=offers,
        raw=item,
    )


def map_search_result(payload: dict[str, Any]) -> SearchResult:
    search_id = payload.get("searchId")
    hotels = [map_hotel(h, search_id=search_id) for h in payload.get("hotels", [])]
    return SearchResult(
        search_id=search_id,
        expires_on=parse_dt(payload.get("expiresOn")),
        hotels=hotels,
    )


def map_booking(item: dict[str, Any]) -> PaximumBooking:
    booking_info = item.get("bookingInfo", item)

    return PaximumBooking(
        booking_id=booking_info.get("id") or item.get("bookingId") or "",
        booking_number=booking_info.get("bookingNumber") or item.get("bookingNumber"),
        order_number=booking_info.get("orderNumber") or item.get("orderNumber"),
        supplier_booking_number=booking_info.get("supplierBookingNumber"),
        status=booking_info.get("status") or item.get("status") or "Unknown",
        payment_status=item.get("paymentStatus"),
        service_type=booking_info.get("serviceType") or item.get("type"),
        checkin=parse_dt(item.get("checkin") or booking_info.get("checkIn")),
        checkout=parse_dt(item.get("checkout") or booking_info.get("checkOut")),
        amount=_money(item.get("amount") or booking_info.get("totalBuyingAmount")),
        cancellation_policies=_cancellation_policies(
            item.get("cancellationPolicies")
            or item.get("hotelBooking", {}).get("cancellationPolicies", {}).get("cancellationPolicy")
        ),
        hotel_id=str(item.get("hotelId") or item.get("hotelInfo", {}).get("hotelCode") or ""),
        notes=item.get("notes", []) or booking_info.get("serviceProviderNotes", []),
        nationality=item.get("nationality"),
        document_url=item.get("documentUrl"),
        total_buying_amount=_money(booking_info.get("totalBuyingAmount")),
        total_selling_amount=_money(booking_info.get("totalSellingAmount")),
        raw=item,
    )
