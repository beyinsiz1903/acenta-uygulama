"""Paximum (San TSG) marketplace proxy router — per-tenant.

Each request loads the calling agency's Paximum credentials (base_url +
bearer_token) from the encrypted `supplier_credentials` collection
(`/api/supplier-credentials/*` UI). No env vars are read.

Auth: super_admin / admin / agency_admin / operator.
All endpoints under `/api/paximum/*`.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_roles
from app.db import get_db
from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials
from app.services.paximum import PaximumClient, PaximumError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paximum", tags=["paximum"])

ROLES = ["super_admin", "admin", "agency_admin", "operator"]
UserDep = Depends(require_roles(ROLES))


def _org_id(user: dict) -> str:
    return user.get("organization_id") or user.get("org_id") or ""


async def _client_for(current_user: dict, db) -> PaximumClient:
    org_id = _org_id(current_user)
    if not org_id:
        raise HTTPException(status_code=400, detail="Aktif kullanıcı bir organizasyona bağlı değil.")
    creds = await get_decrypted_credentials(db, org_id, "paximum")
    if not creds or not creds.get("base_url") or not creds.get("bearer_token"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu acente için Paximum credential'ları tanımlı değil. "
                "Tedarikçi Ayarları > Paximum sayfasından base_url ve bearer_token girin."
            ),
        )
    try:
        return PaximumClient(base_url=creds["base_url"], token=creds["bearer_token"])
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
async def paximum_health(current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    """Per-tenant credential status (does not call upstream)."""
    org_id = _org_id(current_user)
    if not org_id:
        return {"configured": False, "reason": "no_organization"}
    creds = await get_decrypted_credentials(db, org_id, "paximum")
    if not creds:
        return {"configured": False, "reason": "no_credentials", "organization_id": org_id}
    return {
        "configured": bool(creds.get("base_url") and creds.get("bearer_token")),
        "organization_id": org_id,
        "base_url_set": bool(creds.get("base_url")),
        "token_set": bool(creds.get("bearer_token")),
    }


@router.post("/search/hotels")
async def search_hotels(payload: SearchHotelsRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
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
async def search_hotel_details(payload: HotelDetailsRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.hotel_details(payload.hotelId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/search/checkavailability")
async def search_check_availability(payload: OfferIdRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.check_availability(payload.offerId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/search/checkhotelavailability")
async def search_check_hotel_availability(payload: OfferIdRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.check_hotel_availability(payload.offerId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/placeorder")
async def booking_place_order(payload: PlaceOrderRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.place_order(
            travellers=[t.model_dump(exclude_none=True) for t in payload.travellers],
            hotel_bookings=[hb.model_dump(exclude_none=True) for hb in payload.hotelBookings],
            agency_reference_number=payload.agencyReferenceNumber,
        )
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/getbookings")
async def booking_list(payload: GetBookingsRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
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
async def booking_details(payload: BookingDetailsRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.booking_details(
            booking_id=payload.bookingId,
            booking_number=payload.bookingNumber,
            agency_reference_number=payload.agencyReferenceNumber,
        )
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/cancellationfee")
async def booking_cancellation_fee(payload: BookingDetailsRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    if not payload.bookingId:
        raise HTTPException(status_code=400, detail="bookingId zorunlu.")
    try:
        return await cli.cancellation_fee(payload.bookingId)
    except PaximumError as exc:
        _raise(exc)


@router.post("/booking/cancel")
async def booking_cancel(payload: CancelBookingRequest, current_user: dict = UserDep, db=Depends(get_db)) -> Dict[str, Any]:
    cli = await _client_for(current_user, db)
    try:
        return await cli.cancel_booking(
            booking_id=payload.bookingId,
            booking_number=payload.bookingNumber,
        )
    except PaximumError as exc:
        _raise(exc)
