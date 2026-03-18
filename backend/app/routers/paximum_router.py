"""Paximum Supplier Router — Full booking lifecycle endpoints.

Endpoints:
- POST /search         → Hotel search
- POST /hotel-details  → Hotel detail
- POST /check-availability → Offer availability check
- POST /book           → Place order (create booking)
- POST /bookings       → List bookings
- POST /booking-details → Single booking detail
- POST /cancel-fee     → Get cancellation fee
- POST /cancel         → Cancel booking
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.context_org import get_current_org
from app.errors import AppError
from app.services.suppliers.paximum_adapter import (
    PaximumAuthError,
    PaximumError,
    PaximumNotFoundError,
    PaximumRetryableError,
    PaximumValidationError,
    paximum_adapter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suppliers/paximum", tags=["suppliers-paximum"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class DestinationItem(BaseModel):
    type: str = Field(..., description="city | hotel | area")
    id: str


class RoomItem(BaseModel):
    adults: int = 2
    childrenAges: List[int] = Field(default_factory=list)


class PaximumSearchRequest(BaseModel):
    destinations: List[DestinationItem]
    rooms: List[RoomItem]
    checkInDate: str
    checkOutDate: str
    currency: str = "EUR"
    customerNationality: str = "TR"
    onlyBestOffers: bool = False
    filterUnavailable: bool = False
    includeHotelContent: bool = False
    language: str = "en"
    timeout: int = 20


class HotelDetailsRequest(BaseModel):
    hotelId: str


class CheckAvailabilityRequest(BaseModel):
    offerId: str


class PlaceOrderTraveller(BaseModel):
    travellerNo: str
    type: str
    title: str
    name: str
    surname: str
    birthDate: Optional[str] = None
    isLead: bool = False
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    nationality: Optional[str] = None


class PlaceOrderRoom(BaseModel):
    roomId: str
    travellers: List[str]


class PlaceOrderHotelBooking(BaseModel):
    offerId: str
    reservationNote: Optional[str] = None
    rooms: List[PlaceOrderRoom]


class PlaceOrderRequest(BaseModel):
    travellers: List[PlaceOrderTraveller]
    hotelBookings: List[PlaceOrderHotelBooking]
    agencyReferenceNumber: Optional[str] = None


class GetBookingsRequest(BaseModel):
    fromDate: Optional[str] = Field(None, alias="from")
    toDate: Optional[str] = Field(None, alias="to")
    checkInFrom: Optional[str] = None
    checkInTo: Optional[str] = None
    agencyReferenceNumber: Optional[str] = None
    getAllBookingsOfUserAccount: Optional[bool] = None

    model_config = {"populate_by_name": True}


class BookingDetailsRequest(BaseModel):
    bookingId: Optional[str] = None
    bookingNumber: Optional[str] = None
    agencyReferenceNumber: Optional[str] = None


class CancelFeeRequest(BaseModel):
    bookingId: str


class CancelBookingRequest(BaseModel):
    bookingId: Optional[str] = None
    bookingNumber: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trace_id(x_trace_id: Optional[str] = None) -> str:
    return x_trace_id or f"syroce-{uuid.uuid4().hex[:12]}"


def _serialize_money(m):
    if m is None:
        return None
    return {"amount": float(m.amount), "currency": m.currency}


def _serialize_offer(o) -> dict:
    return {
        "offer_id": o.offer_id,
        "search_id": o.search_id,
        "hotel_id": o.hotel_id,
        "board": o.board,
        "board_id": o.board_id,
        "price": _serialize_money(o.price),
        "minimum_sale_price": _serialize_money(o.minimum_sale_price),
        "is_available": o.is_available,
        "is_special": o.is_special,
        "is_b2c_price": o.is_b2c_price,
        "expires_on": o.expires_on.isoformat() if o.expires_on else None,
        "rooms": [
            {
                "room_id": r.room_id,
                "room_type": r.room_type,
                "price": _serialize_money(r.price),
            }
            for r in o.rooms
        ],
        "cancellation_policies": [
            {
                "permitted_date": cp.permitted_date.isoformat() if cp.permitted_date else None,
                "fee": _serialize_money(cp.fee),
            }
            for cp in o.cancellation_policies
        ],
    }


def _serialize_hotel(h) -> dict:
    return {
        "hotel_id": h.hotel_id,
        "name": h.name,
        "description": h.description,
        "city_id": h.city_id,
        "city_name": h.city_name,
        "country_id": h.country_id,
        "country_name": h.country_name,
        "stars": h.stars,
        "rating": h.rating,
        "photos": h.photos,
        "address": h.address,
        "geolocation": h.geolocation,
        "offers": [_serialize_offer(o) for o in h.offers],
    }


def _serialize_booking(b) -> dict:
    return {
        "booking_id": b.booking_id,
        "booking_number": b.booking_number,
        "order_number": b.order_number,
        "supplier_booking_number": b.supplier_booking_number,
        "status": b.status,
        "payment_status": b.payment_status,
        "service_type": b.service_type,
        "checkin": b.checkin.isoformat() if b.checkin else None,
        "checkout": b.checkout.isoformat() if b.checkout else None,
        "amount": _serialize_money(b.amount),
        "hotel_id": b.hotel_id,
        "notes": b.notes,
        "nationality": b.nationality,
        "document_url": b.document_url,
        "total_buying_amount": _serialize_money(b.total_buying_amount),
        "total_selling_amount": _serialize_money(b.total_selling_amount),
        "cancellation_policies": [
            {
                "permitted_date": cp.permitted_date.isoformat() if cp.permitted_date else None,
                "fee": _serialize_money(cp.fee),
            }
            for cp in b.cancellation_policies
        ],
    }


def _map_paximum_error(exc: PaximumError) -> AppError:
    if isinstance(exc, PaximumAuthError):
        return AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="SUPPLIER_AUTH_FAILED",
            message="Paximum authentication failed.",
            details={"supplier": "paximum"},
        )
    if isinstance(exc, PaximumNotFoundError):
        return AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SUPPLIER_NOT_FOUND",
            message=str(exc),
            details={"supplier": "paximum"},
        )
    if isinstance(exc, PaximumValidationError):
        return AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="SUPPLIER_VALIDATION_ERROR",
            message=str(exc),
            details={"supplier": "paximum"},
        )
    if isinstance(exc, PaximumRetryableError):
        return AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="SUPPLIER_UPSTREAM_UNAVAILABLE",
            message="Paximum supplier service is temporarily unavailable.",
            details={"supplier": "paximum", "reason": str(exc)},
        )
    return AppError(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="SUPPLIER_ERROR",
        message=str(exc),
        details={"supplier": "paximum"},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/search", status_code=status.HTTP_200_OK)
async def paximum_search(
    payload: PaximumSearchRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    try:
        result = await paximum_adapter.search_hotels(
            destinations=[d.model_dump() for d in payload.destinations],
            rooms=[r.model_dump() for r in payload.rooms],
            check_in_date=payload.checkInDate,
            check_out_date=payload.checkOutDate,
            currency=payload.currency,
            customer_nationality=payload.customerNationality,
            only_best_offers=payload.onlyBestOffers,
            filter_unavailable=payload.filterUnavailable,
            include_hotel_content=payload.includeHotelContent,
            language=payload.language,
            timeout=payload.timeout,
            trace_id=trace,
        )
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {
        "search_id": result.search_id,
        "expires_on": result.expires_on.isoformat() if result.expires_on else None,
        "hotel_count": len(result.hotels),
        "hotels": [_serialize_hotel(h) for h in result.hotels],
        "trace_id": trace,
    }


@router.post("/hotel-details", status_code=status.HTTP_200_OK)
async def paximum_hotel_details(
    payload: HotelDetailsRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    try:
        hotel = await paximum_adapter.get_hotel_details(payload.hotelId, trace_id=trace)
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {"hotel": _serialize_hotel(hotel), "trace_id": trace}


@router.post("/check-availability", status_code=status.HTTP_200_OK)
async def paximum_check_availability(
    payload: CheckAvailabilityRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    try:
        offer = await paximum_adapter.check_availability(payload.offerId, trace_id=trace)
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {"offer": _serialize_offer(offer), "trace_id": trace}


@router.post("/book", status_code=status.HTTP_200_OK)
async def paximum_place_order(
    payload: PlaceOrderRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    ref = payload.agencyReferenceNumber or f"SYR-{uuid.uuid4().hex[:10].upper()}"

    try:
        result = await paximum_adapter.place_order(
            travellers=[t.model_dump() for t in payload.travellers],
            hotel_bookings=[hb.model_dump() for hb in payload.hotelBookings],
            agency_reference_number=ref,
            trace_id=trace,
        )
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {
        "agency_reference_number": ref,
        "supplier_response": result,
        "trace_id": trace,
    }


@router.post("/bookings", status_code=status.HTTP_200_OK)
async def paximum_get_bookings(
    payload: GetBookingsRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    try:
        bookings = await paximum_adapter.get_bookings(
            from_date=payload.fromDate,
            to_date=payload.toDate,
            checkin_from=payload.checkInFrom,
            checkin_to=payload.checkInTo,
            agency_reference_number=payload.agencyReferenceNumber,
            get_all_bookings_of_user_account=payload.getAllBookingsOfUserAccount,
            trace_id=trace,
        )
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {
        "bookings": [_serialize_booking(b) for b in bookings],
        "count": len(bookings),
        "trace_id": trace,
    }


@router.post("/booking-details", status_code=status.HTTP_200_OK)
async def paximum_booking_details(
    payload: BookingDetailsRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    try:
        booking = await paximum_adapter.get_booking_details(
            booking_id=payload.bookingId,
            booking_number=payload.bookingNumber,
            agency_reference_number=payload.agencyReferenceNumber,
            trace_id=trace,
        )
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {"booking": _serialize_booking(booking), "trace_id": trace}


@router.post("/cancel-fee", status_code=status.HTTP_200_OK)
async def paximum_cancel_fee(
    payload: CancelFeeRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    try:
        fee = await paximum_adapter.get_cancellation_fee(payload.bookingId, trace_id=trace)
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {"cancellation_fee": fee, "trace_id": trace}


@router.post("/cancel", status_code=status.HTTP_200_OK)
async def paximum_cancel_booking(
    payload: CancelBookingRequest,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    x_trace_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    trace = _trace_id(x_trace_id)
    try:
        result = await paximum_adapter.cancel_booking(
            booking_id=payload.bookingId,
            booking_number=payload.bookingNumber,
            trace_id=trace,
        )
    except PaximumError as exc:
        raise _map_paximum_error(exc) from exc

    return {"result": result, "trace_id": trace}
