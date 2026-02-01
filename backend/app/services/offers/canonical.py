from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CanonicalMoney:
    amount: float
    currency: str


@dataclass
class CanonicalHotel:
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class CanonicalStay:
    check_in: str
    check_out: str
    nights: int
    adults: int
    children: int


@dataclass
class CanonicalRoom:
    room_name: Optional[str] = None
    board_type: Optional[str] = None


@dataclass
class CanonicalCancellationPolicy:
    refundable: Optional[bool] = None
    deadline: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class CanonicalHotelOffer:
    offer_token: str
    supplier_code: str
    supplier_offer_id: str
    product_type: str
    hotel: CanonicalHotel
    stay: CanonicalStay
    room: CanonicalRoom
    cancellation_policy: Optional[CanonicalCancellationPolicy]
    price: CanonicalMoney
    availability_token: Optional[str]
    raw_fingerprint: str


def make_raw_fingerprint(raw: Dict[str, Any]) -> str:
    """Compute a stable hash fingerprint for a supplier raw payload.

    NOTE: this is used only for debugging/dedup; raw itself must not be
    exposed via public APIs.
    """
    import hashlib
    import json

    payload = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
