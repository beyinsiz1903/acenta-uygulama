"""Paximum Travel API Adapter.

Supplier capability: Hotel + Transfer + Activity
Auth: Token-based (username/password + agency code)
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .base_adapter import SupplierAdapter

logger = logging.getLogger("suppliers.paximum")


class PaximumAdapter(SupplierAdapter):
    """Paximum multi-product supplier adapter."""

    SUPPLIER_CODE = "paximum"
    PRODUCT_TYPES = ["hotel", "transfer", "activity"]

    def __init__(self, base_url: str, token: str | None = None, timeout: float = 15.0):
        super().__init__(base_url, timeout)
        self.token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def authenticate(self, credentials: dict) -> dict[str, Any]:
        """Authenticate with Paximum."""
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        agency_code = credentials.get("agency_code", "")

        if not username or not password:
            return {"success": False, "error": "username and password required"}

        payload = {"Agency": agency_code, "User": username, "Password": password}
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/authenticationservice/login", json=payload)
            latency_ms = round((time.monotonic() - start) * 1000, 1)

            if resp.status_code == 200:
                data = resp.json()
                body = data.get("body") or data
                token = body.get("token") or body.get("Token") or ""
                if token:
                    self.token = token
                    return {"success": True, "token": token, "latency_ms": latency_ms}
                return {"success": False, "error": "No token in response", "response": str(data)[:200], "latency_ms": latency_ms}
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:300], "latency_ms": latency_ms}
        except Exception as e:
            return {"success": False, "error": str(e), "latency_ms": round((time.monotonic() - start) * 1000, 1)}

    async def search_hotels(self, request: dict) -> dict[str, Any]:
        """Search hotels via Paximum."""
        payload = {
            "checkIn": request.get("checkin", ""),
            "checkOut": request.get("checkout", ""),
            "currency": request.get("currency", "EUR"),
            "nationality": request.get("nationality", "TR"),
            "arrivalLocations": [{"id": request.get("destination", ""), "type": 2}],
            "roomCriteria": request.get("rooms", [{"adult": 2, "childAges": []}]),
        }
        result = await self._post("/api/productservice/getoffers", payload, self._headers())
        if result["success"] and result.get("data"):
            body = result["data"].get("body") or result["data"]
            hotels = body.get("hotels") or body.get("offers") or []
            products = [self._normalize_hotel(h) for h in hotels[:50]]
            result["products"] = products
            result["total"] = len(products)
        return result

    def _normalize_hotel(self, raw: dict) -> dict[str, Any]:
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": "hotel",
            "external_id": str(raw.get("id", raw.get("hotelId", ""))),
            "name": raw.get("name", raw.get("hotelName", "")),
            "location": raw.get("location", {}).get("name", "") if isinstance(raw.get("location"), dict) else str(raw.get("city", "")),
            "star_rating": raw.get("stars", 0),
            "price": raw.get("price", {}).get("amount", 0) if isinstance(raw.get("price"), dict) else raw.get("price", 0),
            "currency": raw.get("price", {}).get("currency", "EUR") if isinstance(raw.get("price"), dict) else "EUR",
            "availability": True,
            "images": raw.get("thumbnailFull", raw.get("images", [""]))[:3] if isinstance(raw.get("thumbnailFull", raw.get("images", [])), list) else [],
            "raw": raw,
        }

    async def search_transfers(self, request: dict) -> dict[str, Any]:
        """Search transfers via Paximum."""
        payload = {
            "date": request.get("date", ""),
            "fromLocation": {"id": request.get("from_location", ""), "type": request.get("from_type", 2)},
            "toLocation": {"id": request.get("to_location", ""), "type": request.get("to_type", 2)},
            "adult": request.get("adults", 2),
            "child": request.get("children", 0),
        }
        result = await self._post("/api/productservice/gettransferoffers", payload, self._headers())
        if result["success"] and result.get("data"):
            body = result["data"].get("body") or result["data"]
            transfers = body.get("transfers") or body.get("offers") or []
            products = []
            for t in transfers[:30]:
                products.append({
                    "supplier": self.SUPPLIER_CODE,
                    "product_type": "transfer",
                    "external_id": str(t.get("id", "")),
                    "name": t.get("name", t.get("vehicleType", "")),
                    "location": f"{request.get('from_location', '')} -> {request.get('to_location', '')}",
                    "price": t.get("price", {}).get("amount", 0) if isinstance(t.get("price"), dict) else t.get("price", 0),
                    "currency": t.get("price", {}).get("currency", "EUR") if isinstance(t.get("price"), dict) else "EUR",
                    "availability": True,
                    "raw": t,
                })
            result["products"] = products
            result["total"] = len(products)
        return result

    async def search_activities(self, request: dict) -> dict[str, Any]:
        """Search activities via Paximum."""
        payload = {
            "date": request.get("date", request.get("start_date", "")),
            "locationId": request.get("destination", ""),
            "adult": request.get("adults", 2),
            "child": request.get("children", 0),
        }
        result = await self._post("/api/productservice/getexcursionoffers", payload, self._headers())
        if result["success"] and result.get("data"):
            body = result["data"].get("body") or result["data"]
            activities = body.get("excursions") or body.get("offers") or []
            products = []
            for a in activities[:30]:
                products.append({
                    "supplier": self.SUPPLIER_CODE,
                    "product_type": "activity",
                    "external_id": str(a.get("id", "")),
                    "name": a.get("name", ""),
                    "location": a.get("locationName", ""),
                    "price": a.get("price", {}).get("amount", 0) if isinstance(a.get("price"), dict) else a.get("price", 0),
                    "currency": a.get("price", {}).get("currency", "EUR") if isinstance(a.get("price"), dict) else "EUR",
                    "availability": True,
                    "raw": a,
                })
            result["products"] = products
            result["total"] = len(products)
        return result

    async def create_booking(self, request: dict) -> dict[str, Any]:
        """Create booking via Paximum."""
        result = await self._post("/api/bookingservice/setbooking", request, self._headers())
        if result["success"] and result.get("data"):
            result["booking"] = self.normalize_booking(result["data"])
        return result

    async def cancel_booking(self, request: dict) -> dict[str, Any]:
        """Cancel booking via Paximum."""
        return await self._post("/api/bookingservice/cancelbooking", {
            "bookingNumber": request.get("booking_id", ""),
        }, self._headers())
