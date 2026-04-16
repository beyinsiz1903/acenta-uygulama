"""RateHawk Hotel API Adapter.

Supplier capability: Hotel
Auth: API key based (Basic auth with key_id:api_key)
Docs reference: https://docs.emergingtravel.com/docs/b2b-api/
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Any

import httpx

from .base_adapter import SupplierAdapter

logger = logging.getLogger("suppliers.ratehawk")


class RateHawkAdapter(SupplierAdapter):
    """RateHawk B2B Hotel supplier adapter."""

    SUPPLIER_CODE = "ratehawk"
    PRODUCT_TYPES = ["hotel"]

    def __init__(self, base_url: str, token: str | None = None, timeout: float = 15.0):
        super().__init__(base_url, timeout)
        self.token = token  # base64(key_id:api_key)

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Basic {self.token}"
        return h

    async def authenticate(self, credentials: dict) -> dict[str, Any]:
        """RateHawk uses Basic auth — key_id:api_key encoded in base64."""
        key_id = credentials.get("key_id", "")
        api_key = credentials.get("api_key", "")
        if not key_id or not api_key:
            return {"success": False, "error": "key_id and api_key required"}

        token = base64.b64encode(f"{key_id}:{api_key}".encode()).decode()
        self.token = token

        # Test auth by calling a lightweight endpoint
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/b2b/v3/search/region/",
                    json={"query": "istanbul", "language": "en"},
                    headers=self._headers(),
                )
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            if resp.status_code == 200:
                return {"success": True, "token": token, "latency_ms": latency_ms}
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:300], "latency_ms": latency_ms}
        except Exception as e:
            return {"success": False, "error": str(e), "latency_ms": round((time.monotonic() - start) * 1000, 1)}

    async def search_hotels(self, request: dict) -> dict[str, Any]:
        """Search hotels via RateHawk.

        request keys: checkin, checkout, destination, guests, residency, currency
        """
        payload = {
            "checkin": request.get("checkin", ""),
            "checkout": request.get("checkout", ""),
            "destination": request.get("destination", ""),
            "guests": request.get("guests", [{"adults": 2}]),
            "residency": request.get("residency", "tr"),
            "currency": request.get("currency", "USD"),
        }
        result = await self._post("/api/b2b/v3/search/serp/hotels/", payload, self._headers())
        if result["success"] and result.get("data"):
            products = []
            for hotel in (result["data"].get("hotels") or [])[:50]:
                products.append(self.normalize_product(hotel, "hotel"))
            result["products"] = products
            result["total"] = len(products)
        return result

    def normalize_product(self, raw: dict, product_type: str) -> dict[str, Any]:
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": product_type,
            "external_id": str(raw.get("id", raw.get("hotel_id", ""))),
            "name": raw.get("name", raw.get("hotel_name", "")),
            "location": raw.get("region", {}).get("name", "") if isinstance(raw.get("region"), dict) else str(raw.get("region", "")),
            "star_rating": raw.get("star_rating", 0),
            "price": raw.get("min_price", raw.get("price", 0)),
            "currency": raw.get("currency", "USD"),
            "availability": True,
            "images": raw.get("images", [])[:3],
            "raw": raw,
        }

    async def get_availability(self, request: dict) -> dict[str, Any]:
        """Check hotel room availability."""
        return await self._post("/api/b2b/v3/search/hp/", {
            "id": request.get("hotel_id", ""),
            "checkin": request.get("checkin", ""),
            "checkout": request.get("checkout", ""),
            "guests": request.get("guests", [{"adults": 2}]),
            "currency": request.get("currency", "USD"),
        }, self._headers())

    async def create_booking(self, request: dict) -> dict[str, Any]:
        """Create hotel booking."""
        result = await self._post("/api/b2b/v3/hotel/order/booking/form/", request, self._headers())
        if result["success"] and result.get("data"):
            result["booking"] = self.normalize_booking(result["data"])
        return result

    async def cancel_booking(self, request: dict) -> dict[str, Any]:
        """Cancel hotel booking."""
        return await self._post("/api/b2b/v3/hotel/order/booking/cancel/", {
            "partner_order_id": request.get("booking_id", ""),
        }, self._headers())
