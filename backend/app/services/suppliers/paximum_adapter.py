from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from .paximum_mapping import map_booking, map_hotel, map_offer, map_search_result
from .paximum_models import Hotel, Offer, PaximumBooking, SearchResult

logger = logging.getLogger(__name__)


class PaximumError(Exception):
    pass


class PaximumAuthError(PaximumError):
    pass


class PaximumOfferExpiredError(PaximumError):
    pass


class PaximumValidationError(PaximumError):
    pass


class PaximumRetryableError(PaximumError):
    pass


class PaximumNotFoundError(PaximumError):
    pass


class PaximumAdapter:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: int = 45,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _headers(self, trace_id: Optional[str] = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.token}",
        }
        if trace_id:
            headers["X-Trace-Id"] = trace_id
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.request(
                        method=method,
                        url=url,
                        headers=self._headers(trace_id),
                        json=json_body,
                    )

                if resp.status_code in (401, 403):
                    raise PaximumAuthError("Paximum authentication failed")

                if resp.status_code in (408, 429, 500, 502, 503, 504):
                    raise PaximumRetryableError(
                        f"Retryable Paximum error: {resp.status_code} {resp.text}"
                    )

                if resp.status_code >= 400:
                    raise PaximumValidationError(
                        f"Paximum request failed: {resp.status_code} {resp.text}"
                    )

                return resp.json()

            except (httpx.ReadTimeout, httpx.ConnectTimeout, PaximumRetryableError) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                delay = min(2 ** (attempt - 1), 8) + random.uniform(0, 0.5)
                logger.warning("Paximum retry %s/%s in %.2fs: %s", attempt, self.max_retries, delay, exc)
                await asyncio.sleep(delay)
            except httpx.HTTPError as exc:
                raise PaximumError(f"Paximum HTTP error: {exc}") from exc

        raise PaximumRetryableError(f"Paximum request exhausted retries: {last_exc}")

    async def authenticate(self, trace_id: Optional[str] = None) -> bool:
        payload = {
            "destinations": [{"type": "city", "id": "1"}],
            "rooms": [{"adults": 1, "childrenAges": []}],
            "checkInDate": "2030-01-10",
            "checkOutDate": "2030-01-11",
            "currency": "EUR",
            "customerNationality": "TR",
            "timeOut": 1,
            "onlyBestOffers": True,
        }
        try:
            await self._request("POST", "/v1/search/hotels", payload, trace_id)
            return True
        except PaximumAuthError:
            return False

    async def search_hotels(
        self,
        *,
        destinations: list[dict[str, str]],
        rooms: list[dict[str, Any]],
        check_in_date: str,
        check_out_date: str,
        currency: str,
        customer_nationality: str,
        filter_unavailable: bool = False,
        filter_distinct: bool = False,
        with_promotion: bool = False,
        include_hotel_content: bool = False,
        only_best_offers: bool = False,
        language: str = "en",
        timeout: int = 20,
        is_pre_search: bool = False,
        trace_id: Optional[str] = None,
    ) -> SearchResult:
        hotel_count = sum(1 for d in destinations if d.get("type") == "hotel")
        if hotel_count > 200:
            raise PaximumValidationError("Maximum 200 hotel destinations per request")

        if len(rooms) > 4:
            raise PaximumValidationError("Maximum 4 rooms per request")

        total_adults = sum(int(r.get("adults", 0)) for r in rooms)
        if total_adults > 20:
            raise PaximumValidationError("Maximum 20 adults per request")

        payload = {
            "destinations": destinations,
            "rooms": rooms,
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "currency": currency,
            "customerNationality": customer_nationality,
            "filterUnavailable": filter_unavailable,
            "filterDistinct": filter_distinct,
            "withPromotion": with_promotion,
            "includeHotelContent": include_hotel_content,
            "onlyBestOffers": only_best_offers,
            "language": language,
            "timeOut": timeout,
            "isPreSearch": is_pre_search,
        }
        data = await self._request("POST", "/v1/search/hotels", payload, trace_id)
        return map_search_result(data)

    async def get_hotel_details(self, hotel_id: str, trace_id: Optional[str] = None) -> Hotel:
        data = await self._request(
            "POST",
            "/v1/search/hoteldetails",
            {"hotelId": hotel_id},
            trace_id,
        )
        return map_hotel(data)

    async def check_availability(self, offer_id: str, trace_id: Optional[str] = None) -> Offer:
        data = await self._request(
            "POST",
            "/v1/search/checkavailability",
            {"offerId": offer_id},
            trace_id,
        )
        offer = map_offer(data, search_id=data.get("searchId"))
        if not offer.is_available:
            raise PaximumValidationError("Offer is not available")
        return offer

    async def check_hotel_availability(self, offer_id: str, trace_id: Optional[str] = None) -> list[Offer]:
        data = await self._request(
            "POST",
            "/v1/search/checkhotelavailability",
            {"offerId": offer_id},
            trace_id,
        )
        search_id = data.get("searchId")
        offers = [map_offer(x, search_id=search_id) for x in data.get("offers", [])]
        return [o for o in offers if o.is_available]

    async def place_order(
        self,
        *,
        travellers: list[dict[str, Any]],
        hotel_bookings: list[dict[str, Any]],
        agency_reference_number: str,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        payload = {
            "travellers": travellers,
            "hotelBookings": hotel_bookings,
            "agencyReferenceNumber": agency_reference_number,
        }
        return await self._request("POST", "/v1/booking/placeorder", payload, trace_id)

    async def get_bookings(
        self,
        *,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        checkin_from: Optional[str] = None,
        checkin_to: Optional[str] = None,
        agency_reference_number: Optional[str] = None,
        get_all_bookings_of_user_account: Optional[bool] = None,
        trace_id: Optional[str] = None,
    ) -> list[PaximumBooking]:
        payload: dict[str, Any] = {}
        if from_date:
            payload["from"] = from_date
        if to_date:
            payload["to"] = to_date
        if checkin_from:
            payload["checkInFrom"] = checkin_from
        if checkin_to:
            payload["checkInTo"] = checkin_to
        if agency_reference_number:
            payload["agencyReferenceNumber"] = agency_reference_number
        if get_all_bookings_of_user_account is not None:
            payload["getAllBookingsOfUserAccount"] = get_all_bookings_of_user_account

        data = await self._request("POST", "/v1/booking/getbookings", payload, trace_id)
        return [map_booking(x) for x in data.get("bookings", [])]

    async def get_booking_details(
        self,
        *,
        booking_id: Optional[str] = None,
        booking_number: Optional[str] = None,
        agency_reference_number: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> PaximumBooking:
        payload: dict[str, Any] = {}
        if booking_id:
            payload["bookingId"] = booking_id
        elif booking_number:
            payload["bookingNumber"] = booking_number
        elif agency_reference_number:
            payload["agencyReferenceNumber"] = agency_reference_number
        else:
            raise PaximumValidationError("One of booking_id, booking_number, agency_reference_number is required")

        data = await self._request("POST", "/v1/booking/getbuyerbooking", payload, trace_id)
        if "bookingInfo" not in data and not data:
            raise PaximumNotFoundError("Booking details not found")
        return map_booking(data)

    async def get_cancellation_fee(self, booking_id: str, trace_id: Optional[str] = None) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/booking/getcancellationfee",
            {"bookingId": booking_id},
            trace_id,
        )

    async def cancel_booking(
        self,
        *,
        booking_id: Optional[str] = None,
        booking_number: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if booking_id:
            payload["bookingId"] = booking_id
        elif booking_number:
            payload["bookingNumber"] = booking_number
        else:
            raise PaximumValidationError("booking_id or booking_number is required")

        return await self._request("POST", "/v1/booking/cancel", payload, trace_id)

    async def poll_booking_confirmation(
        self,
        *,
        agency_reference_number: str,
        max_wait_seconds: int = 120,
        trace_id: Optional[str] = None,
    ) -> PaximumBooking:
        started = datetime.now(timezone.utc)
        intervals = [5, 10, 20, 30, 30, 30]

        for delay in intervals:
            bookings = await self.get_bookings(
                agency_reference_number=agency_reference_number,
                trace_id=trace_id,
            )
            if bookings:
                booking = bookings[0]
                if booking.status.lower() in {"confirmed", "cancelled", "rejected", "pending", "onrequest"}:
                    return booking

            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            if elapsed >= max_wait_seconds:
                break
            await asyncio.sleep(delay)

        raise PaximumRetryableError("Booking polling timed out")


# ---------------------------------------------------------------------------
# Sprint 3 compat shim (DEPRECATED — DO NOT USE IN NEW CODE).
#
# The legacy `paximum_adapter` singleton previously read PAXIMUM_API_KEY from
# the global environment, which was a cross-tenant credential leak surface.
# All production routes now use per-tenant credentials loaded from the
# encrypted `supplier_credentials` collection (see _adapter_for in
# `app/modules/supplier/routers/paximum_router.py`).
#
# This singleton remains only for backward compatibility with the unmounted
# `services/supplier_search_service.search_paximum_offers` function and
# Sprint 3 exit-gate tests (currently `@pytest.mark.skipif(True)`).
# It is created lazily so import-time has no env coupling.
# ---------------------------------------------------------------------------

_paximum_adapter_singleton: Optional["PaximumAdapter"] = None


def _create_default_adapter() -> PaximumAdapter:
    from app.config import PAXIMUM_API_KEY, PAXIMUM_BASE_URL, PAXIMUM_TIMEOUT_SECONDS

    return PaximumAdapter(
        base_url=PAXIMUM_BASE_URL,
        token=PAXIMUM_API_KEY,
        timeout_seconds=int(PAXIMUM_TIMEOUT_SECONDS or 45),
    )


def __getattr__(name: str):
    """Lazy-create the legacy singleton on first attribute access only."""
    global _paximum_adapter_singleton
    if name == "paximum_adapter":
        if _paximum_adapter_singleton is None:
            _paximum_adapter_singleton = _create_default_adapter()
        return _paximum_adapter_singleton
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
