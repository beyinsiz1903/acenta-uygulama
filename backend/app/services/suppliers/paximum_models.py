from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return None


@dataclass(slots=True)
class Money:
    amount: Decimal
    currency: str


@dataclass(slots=True)
class CancellationPolicy:
    permitted_date: Optional[datetime]
    fee: Money


@dataclass(slots=True)
class Traveller:
    type: str
    age: Optional[int]
    nationality: Optional[str]
    traveller_no: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    is_lead: Optional[bool] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None


@dataclass(slots=True)
class Room:
    room_id: str
    room_type: str
    room_type_id: Optional[str]
    travellers: list[Traveller] = field(default_factory=list)
    price: Optional[Money] = None
    promotions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Offer:
    offer_id: str
    search_id: Optional[str]
    hotel_id: str
    expires_on: Optional[datetime]
    board: Optional[str]
    board_id: Optional[str]
    board_categories: list[str]
    rooms: list[Room]
    price: Money
    minimum_sale_price: Optional[Money]
    is_b2c_price: bool
    is_special: bool
    is_available: bool
    cancellation_policies: list[CancellationPolicy]
    restrictions: list[dict[str, Any]]
    warnings: list[str]
    notes: list[str]
    supplements: list[dict[str, Any]]
    raw: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if not self.expires_on:
            return False
        now = now or datetime.now(timezone.utc)
        expires = self.expires_on
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now >= expires


@dataclass(slots=True)
class Hotel:
    hotel_id: str
    name: str
    description: Optional[str]
    city_id: Optional[str]
    city_name: Optional[str]
    country_id: Optional[str]
    country_name: Optional[str]
    stars: Optional[float]
    rating: Optional[float]
    review_url: Optional[str]
    photos: list[str]
    themes: list[str]
    facilities: list[Any]
    content: list[dict[str, Any]]
    address: dict[str, Any]
    geolocation: dict[str, Any]
    offers: list[Offer] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResult:
    search_id: Optional[str]
    expires_on: Optional[datetime]
    hotels: list[Hotel]


@dataclass(slots=True)
class PaximumBooking:
    booking_id: str
    booking_number: Optional[str]
    order_number: Optional[str]
    supplier_booking_number: Optional[str]
    status: str
    payment_status: Optional[str]
    service_type: Optional[str]
    checkin: Optional[datetime]
    checkout: Optional[datetime]
    amount: Optional[Money]
    cancellation_policies: list[CancellationPolicy]
    hotel_id: Optional[str]
    notes: list[str]
    nationality: Optional[str]
    document_url: Optional[str] = None
    total_buying_amount: Optional[Money] = None
    total_selling_amount: Optional[Money] = None
    raw: dict[str, Any] = field(default_factory=dict)
