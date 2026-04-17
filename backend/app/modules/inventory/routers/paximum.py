"""Paximum (San TSG) marketplace proxy router.

Thin per-request proxy over `PaximumClient`. Auth: admin or operator.
All endpoints under `/api/paximum/*`. Errors are translated to HTTP via
`PaximumError`'s status_code and message.

Phase 1 surface (no local persistence yet — v2 will mirror bookings into
`agency_reservations` similar to syroce_marketplace).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.services.paximum import PaximumClient, PaximumError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paximum", tags=["paximum"])

UserDep = Depends(require_roles(["super_admin", "admin", "operator"]))


def _client() -> PaximumClient:
    try:
        return PaximumClient()
    except PaximumError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def _raise(exc: PaximumError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ───────────────── Schemas ─────────────────

class Destination(BaseModel):
    type: str = Field(..., description="'city' or 'hotel'")
    id: str


class Room(BaseModel):
    adults: int = Field(..., ge=1, le=9)
    childrenAges: List[int] = Field(default_factory=list)


class SearchHotelsRequest(BaseModel):
    destinations: List[Destination] = Field(..., max_length=200)
    rooms: List[Room] = Field(..., max_length=4)
    checkinDate: str = Field(..., description="yyyy-MM-dd")
    checkoutDate: str = Field(..., description="yyyy-MM-dd")
    currency: str = "EUR"
    customerNationality: str = "TR"
    language: str = "tr"
    onlyBestOffers: bool = True
    includeHotelContent: bool = False
    filterUnavailable: bool = True
    withPromotion: bool = False
    isPreSearch: bool = False
    timeoutSeconds: int = 0


class HotelDetailsRequest(BaseModel):
    hotelId: str


class OfferIdRequest(BaseModel):
    offerId: str


class Traveller(BaseModel):
    travellerNo: str
    type: str  # adult/child/infant
    title: str  # Mr/Ms/Mrs/Mss/Chd/Inf
    name: str
    surname: str
    isLead: bool = False
    birthDate: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    nationality: str


class HotelBookingRoom(BaseModel):
    roomId: str
    travellers: List[str]


class HotelBooking(BaseModel):
    offerId: str
    reservationNote: Optional[str] = None
    rooms: List[HotelBookingRoom]


class PlaceOrderRequest(BaseModel):
    travellers: List[Traveller]
    hotelBookings: List[HotelBooking]
    agencyReferenceNumber: str


class GetBookingsRequest(BaseModel):
    fromDate: Optional[str] = None
    toDate: Optional[str] = None
    checkinFrom: Optional[str] = None
    checkinTo: Optional[str] = None
    agencyReferenceNumber: Optional[str] = None
    getAll: bool = False


class BookingDetailsRequest(BaseModel):
    bookingId: Optional[str] = None
    bookingNumber: Optional[str] = None
    agencyReferenceNumber: Optional[str] = None


class CancelBookingRequest(BaseModel):
    bookingId: Optional[str] = None
    bookingNumber: Optional[str] = None


# ───────────────── Endpoints ─────────────────

@router.get("/health")
async def paximum_health(_user: dict = UserDep) -> Dict[str, Any]:
    """Lightweight credential check — confirms env vars are set."""
    import os
    has_url = bool(os.environ.get("PAXIMUM_BASE_URL"))
    has_token = bool(os.environ.get("PAXIMUM_BEARER_TOKEN"))
    return {
        "configured": has_url and has_token,
        "base_url_set": has_url,
        "token_set": has_token,
    }


@router.post("/search/hotels")
async def search_hotels(payload: SearchHotelsRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.search_hotels(
            destinations=[d.model_dump() for d in payload.destinations],
            rooms=[r.model_dump() for r in payload.rooms],
            checkin_date=payload.checkinDate,
            checkout_date=payload.checkoutDate,
            currency=payload.currency,
            customer_nationality=payload.customerNationality,
            language=payload.language,
            only_best_offers=payload.onlyBestOffers,
            include_hotel_content=payload.includeHotelContent,
            filter_unavailable=payload.filterUnavailable,
            with_promotion=payload.withPromotion,
            is_pre_search=payload.isPreSearch,
            timeout_seconds=payload.timeoutSeconds,
        )
    except PaximumError as exc:
        _raise(exc)


@router.post("/search/hoteldetails")
async def search_hotel_details(payload: HotelDetailsRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.hotel_details(payload.hotelId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/search/checkavailability")
async def search_check_availability(payload: OfferIdRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.check_availability(payload.offerId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/search/checkhotelavailability")
async def search_check_hotel_availability(payload: OfferIdRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.check_hotel_availability(payload.offerId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/placeorder")
async def booking_place_order(payload: PlaceOrderRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.place_order(
            travellers=[t.model_dump(exclude_none=True) for t in payload.travellers],
            hotel_bookings=[hb.model_dump(exclude_none=True) for hb in payload.hotelBookings],
            agency_reference_number=payload.agencyReferenceNumber,
        )
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/getbookings")
async def booking_list(payload: GetBookingsRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.get_bookings(
            from_date=payload.fromDate,
            to_date=payload.toDate,
            checkin_from=payload.checkinFrom,
            checkin_to=payload.checkinTo,
            agency_reference_number=payload.agencyReferenceNumber,
            get_all=payload.getAll,
        )
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/details")
async def booking_details(payload: BookingDetailsRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.booking_details(
            booking_id=payload.bookingId,
            booking_number=payload.bookingNumber,
            agency_reference_number=payload.agencyReferenceNumber,
        )
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/cancellationfee")
async def booking_cancellation_fee(payload: BookingDetailsRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    if not payload.bookingId:
        raise HTTPException(status_code=400, detail="bookingId zorunlu.")
    try:
        return await cli.cancellation_fee(payload.bookingId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/cancel")
async def booking_cancel(payload: CancelBookingRequest, _user: dict = UserDep) -> Dict[str, Any]:
    cli = _client()
    try:
        return await cli.cancel_booking(
            booking_id=payload.bookingId,
            booking_number=payload.bookingNumber,
        )
    except PaximumError as exc:
        _raise(exc)
