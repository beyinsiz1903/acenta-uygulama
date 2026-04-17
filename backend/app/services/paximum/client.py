"""Async HTTP client for Paximum (San TSG) marketplace — per-tenant.

All endpoints are POST with JSON body and Bearer token auth. Credentials are
NOT read from environment variables — they are loaded by the router from the
encrypted `supplier_credentials` collection (per-agency). The constructor
requires explicit `base_url` and `token` arguments.

This client keeps the surface intentionally thin — a `_post` helper plus
one method per documented endpoint. Higher-level orchestration (search→
checkAvailability→placeOrder) lives in the proxy router.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.services.paximum.errors import PaximumError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0


class PaximumClient:
    """Stateless wrapper around the Paximum REST API."""

    def __init__(self, *, base_url: str, token: str,
                 timeout: float = DEFAULT_TIMEOUT_SECONDS):
        if not base_url or not token:
            raise PaximumError(400, "Paximum credentials eksik (base_url/bearer_token).")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    # ───────────────── Low-level helper ─────────────────

    async def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as cli:
                resp = await cli.post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            logger.warning("Paximum timeout %s: %s", path, exc)
            raise PaximumError(504, f"Paximum yanıt vermedi (timeout): {path}") from exc
        except httpx.HTTPError as exc:
            logger.warning("Paximum network error %s: %s", path, exc)
            raise PaximumError(502, f"Paximum bağlantı hatası: {exc}") from exc

        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except Exception:
                payload = {"raw": resp.text[:500]}
            msg = (
                payload.get("message")
                or payload.get("error", {}).get("message")
                or f"Paximum hata yanıtı ({resp.status_code})"
            )
            logger.warning("Paximum %s -> %s: %s", path, resp.status_code, msg)
            raise PaximumError(resp.status_code, msg, payload=payload)

        try:
            return resp.json()
        except Exception as exc:
            raise PaximumError(502, f"Paximum geçersiz JSON döndürdü: {exc}") from exc

    # ───────────────── Search endpoints ─────────────────

    async def search_hotels(
        self,
        *,
        destinations: List[Dict[str, str]],
        rooms: List[Dict[str, Any]],
        checkin_date: str,
        checkout_date: str,
        currency: str = "EUR",
        customer_nationality: str = "TR",
        language: str = "tr",
        only_best_offers: bool = True,
        include_hotel_content: bool = False,
        filter_unavailable: bool = True,
        with_promotion: bool = False,
        is_pre_search: bool = False,
        timeout_seconds: int = 0,
    ) -> Dict[str, Any]:
        """POST /v1/search/hotels"""
        body = {
            "destinations": destinations,
            "rooms": rooms,
            "checkinDate": checkin_date,
            "checkoutDate": checkout_date,
            "currency": currency,
            "customerNationality": customer_nationality,
            "language": language,
            "onlyBestOffers": only_best_offers,
            "includeHotelContent": include_hotel_content,
            "filterUnavailable": filter_unavailable,
            "withPromotion": with_promotion,
            "isPreSearch": is_pre_search,
            "timeout": timeout_seconds,
        }
        return await self._post("/v1/search/hotels", body)

    async def hotel_details(self, hotel_id: str) -> Dict[str, Any]:
        """POST /v1/search/hoteldetails"""
        return await self._post("/v1/search/hoteldetails", {"hotelId": str(hotel_id)})

    async def check_availability(self, offer_id: str) -> Dict[str, Any]:
        """POST /v1/search/checkavailability — single offer (use when OnlyBestOffers=false)."""
        return await self._post("/v1/search/checkavailability", {"offerId": offer_id})

    async def check_hotel_availability(self, offer_id: str) -> Dict[str, Any]:
        """POST /v1/search/checkhotelavailability — all offers for hotel (OnlyBestOffers=true)."""
        return await self._post("/v1/search/checkhotelavailability", {"offerId": offer_id})

    # ───────────────── Booking endpoints ─────────────────

    async def place_order(
        self,
        *,
        travellers: List[Dict[str, Any]],
        hotel_bookings: List[Dict[str, Any]],
        agency_reference_number: str,
    ) -> Dict[str, Any]:
        """POST /v1/booking/placeorder"""
        body = {
            "travellers": travellers,
            "hotelBookings": hotel_bookings,
            "AgencyReferenceNumber": agency_reference_number,
        }
        return await self._post("/v1/booking/placeorder", body)

    async def get_bookings(
        self,
        *,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        checkin_from: Optional[str] = None,
        checkin_to: Optional[str] = None,
        agency_reference_number: Optional[str] = None,
        get_all: bool = False,
    ) -> Dict[str, Any]:
        """POST /v1/booking/getbookings"""
        body: Dict[str, Any] = {"GetAllBookingsOfUserAccount": get_all}
        if from_date:
            body["from"] = from_date
        if to_date:
            body["to"] = to_date
        if checkin_from:
            body["checkinfrom"] = checkin_from
        if checkin_to:
            body["checkinto"] = checkin_to
        if agency_reference_number:
            body["agencyReferenceNumber"] = agency_reference_number
        return await self._post("/v1/booking/getbookings", body)

    async def booking_details(
        self,
        *,
        booking_id: Optional[str] = None,
        booking_number: Optional[str] = None,
        agency_reference_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v1/booking/getbuyerbooking — exactly one identifier required."""
        body: Dict[str, Any] = {}
        if booking_id:
            body["bookingId"] = booking_id
        elif booking_number:
            body["bookingNumber"] = booking_number
        elif agency_reference_number:
            body["agencyReferenceNumber"] = agency_reference_number
        else:
            raise PaximumError(400, "bookingId, bookingNumber veya agencyReferenceNumber gerekli.")
        return await self._post("/v1/booking/getbuyerbooking", body)

    async def cancellation_fee(self, booking_id: str) -> Dict[str, Any]:
        """POST /v1/booking/getcancellationfee"""
        return await self._post("/v1/booking/getcancellationfee", {"bookingId": booking_id})

    async def cancel_booking(
        self,
        *,
        booking_id: Optional[str] = None,
        booking_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v1/booking/cancel — provide ONE of bookingId or bookingNumber."""
        if not (booking_id or booking_number):
            raise PaximumError(400, "bookingId veya bookingNumber gerekli.")
        body = {"bookingId": booking_id} if booking_id else {"bookingNumber": booking_number}
        return await self._post("/v1/booking/cancel", body)
