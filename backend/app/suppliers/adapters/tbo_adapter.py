"""TBO (TravelBoutique Online) API Adapter.

Supplier capability: Hotel + Flight + Tour
Auth: Username/Password based with token endpoint
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .base_adapter import SupplierAdapter

logger = logging.getLogger("suppliers.tbo")


class TBOAdapter(SupplierAdapter):
    """TBO multi-product supplier adapter."""

    SUPPLIER_CODE = "tbo"
    PRODUCT_TYPES = ["hotel", "flight", "tour"]

    def __init__(self, base_url: str, token: str | None = None, timeout: float = 15.0):
        super().__init__(base_url, timeout)
        self.token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def authenticate(self, credentials: dict) -> dict[str, Any]:
        """Authenticate with TBO using username/password."""
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        client_id = credentials.get("client_id", "")
        if not username or not password:
            return {"success": False, "error": "username and password required"}

        payload = {
            "UserName": username,
            "Password": password,
        }
        if client_id:
            payload["ClientId"] = client_id

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/auth/token",
                    json=payload,
                )
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("Token") or data.get("token") or data.get("TokenId") or ""
                if token:
                    self.token = token
                    return {"success": True, "token": token, "latency_ms": latency_ms}
                return {"success": False, "error": "No token in response", "response": str(data)[:200], "latency_ms": latency_ms}
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:300], "latency_ms": latency_ms}
        except Exception as e:
            return {"success": False, "error": str(e), "latency_ms": round((time.monotonic() - start) * 1000, 1)}

    async def search_hotels(self, request: dict) -> dict[str, Any]:
        """Search hotels via TBO."""
        payload = {
            "CheckIn": request.get("checkin", ""),
            "CheckOut": request.get("checkout", ""),
            "CityCode": request.get("destination", ""),
            "GuestNationality": request.get("nationality", "TR"),
            "PaxRooms": request.get("rooms", [{"Adults": 2, "Children": 0}]),
            "ResponseTime": request.get("response_time", 30),
            "IsDetailedResponse": True,
            "Filters": {"MealType": "All", "Refundable": "All"},
        }
        result = await self._post("/api/hotel/search", payload, self._headers())
        if result["success"] and result.get("data"):
            hotels = result["data"].get("HotelResult") or result["data"].get("Hotels") or []
            products = [self._normalize_hotel(h) for h in hotels[:50]]
            result["products"] = products
            result["total"] = len(products)
        return result

    def _normalize_hotel(self, raw: dict) -> dict[str, Any]:
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": "hotel",
            "external_id": str(raw.get("HotelCode", raw.get("ResultIndex", ""))),
            "name": raw.get("HotelName", ""),
            "location": raw.get("HotelAddress", ""),
            "star_rating": raw.get("StarRating", 0),
            "price": raw.get("Price", {}).get("PublishedPrice", 0) if isinstance(raw.get("Price"), dict) else raw.get("Price", 0),
            "currency": raw.get("Price", {}).get("CurrencyCode", "USD") if isinstance(raw.get("Price"), dict) else "USD",
            "availability": True,
            "raw": raw,
        }

    async def search_flights(self, request: dict) -> dict[str, Any]:
        """Search flights via TBO."""
        payload = {
            "Origin": request.get("origin", ""),
            "Destination": request.get("destination", ""),
            "DepartureDate": request.get("departure_date", ""),
            "ReturnDate": request.get("return_date", ""),
            "AdultCount": request.get("adults", 1),
            "ChildCount": request.get("children", 0),
            "InfantCount": request.get("infants", 0),
            "JourneyType": request.get("journey_type", 1),  # 1=OneWay, 2=Return
            "DirectFlight": request.get("direct", False),
        }
        result = await self._post("/api/flight/search", payload, self._headers())
        if result["success"] and result.get("data"):
            flights = result["data"].get("Results") or []
            products = [self._normalize_flight(f) for f in flights[:50]]
            result["products"] = products
            result["total"] = len(products)
        return result

    def _normalize_flight(self, raw: dict) -> dict[str, Any]:
        segments = raw.get("Segments", [[]])
        first_seg = segments[0][0] if segments and segments[0] else {}
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": "flight",
            "external_id": str(raw.get("ResultIndex", "")),
            "name": f"{first_seg.get('Origin', {}).get('Airport', {}).get('AirportCode', '')} -> {first_seg.get('Destination', {}).get('Airport', {}).get('AirportCode', '')}",
            "location": first_seg.get("Origin", {}).get("Airport", {}).get("CityName", ""),
            "airline": first_seg.get("Airline", {}).get("AirlineName", ""),
            "price": raw.get("Fare", {}).get("PublishedFare", 0) if isinstance(raw.get("Fare"), dict) else 0,
            "currency": raw.get("Fare", {}).get("Currency", "USD") if isinstance(raw.get("Fare"), dict) else "USD",
            "availability": True,
            "raw": raw,
        }

    async def search_tours(self, request: dict) -> dict[str, Any]:
        """Search tours via TBO."""
        payload = {
            "CityCode": request.get("destination", ""),
            "FromDate": request.get("start_date", ""),
            "ToDate": request.get("end_date", ""),
            "AdultCount": request.get("adults", 2),
            "ChildCount": request.get("children", 0),
        }
        result = await self._post("/api/activity/search", payload, self._headers())
        if result["success"] and result.get("data"):
            activities = result["data"].get("Activities") or []
            products = [self._normalize_tour(a) for a in activities[:50]]
            result["products"] = products
            result["total"] = len(products)
        return result

    def _normalize_tour(self, raw: dict) -> dict[str, Any]:
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": "tour",
            "external_id": str(raw.get("ActivityCode", raw.get("ResultIndex", ""))),
            "name": raw.get("ActivityName", ""),
            "location": raw.get("CityName", ""),
            "price": raw.get("Price", {}).get("PublishedPrice", 0) if isinstance(raw.get("Price"), dict) else raw.get("Price", 0),
            "currency": raw.get("Price", {}).get("CurrencyCode", "USD") if isinstance(raw.get("Price"), dict) else "USD",
            "availability": True,
            "raw": raw,
        }

    async def create_booking(self, request: dict) -> dict[str, Any]:
        """Create booking via TBO."""
        result = await self._post("/api/hotel/book", request, self._headers())
        if result["success"] and result.get("data"):
            result["booking"] = self.normalize_booking(result["data"])
        return result

    async def cancel_booking(self, request: dict) -> dict[str, Any]:
        """Cancel booking via TBO."""
        return await self._post("/api/hotel/cancel", {
            "BookingId": request.get("booking_id", ""),
            "RequestType": request.get("request_type", 4),  # 4=Cancel
        }, self._headers())
