"""WTatil Tour API Adapter — Production-grade B2B integration.

Implements the full wtatil.com Tour API flow:
  Auth -> GetAll Tours -> Search Tour -> Add Basket -> Create Booking

Per-agency credentials model: each agency provides their own wtatil credentials.
Token caching per agency (24h validity).

Now extends base SupplierAdapter for unified interface.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .base_adapter import SupplierAdapter

logger = logging.getLogger("suppliers.wtatil")


class WTatilAdapter(SupplierAdapter):
    """HTTP client for WTatil Tour API."""

    SUPPLIER_CODE = "wtatil"
    PRODUCT_TYPES = ["tour"]

    def __init__(self, base_url: str, token: str | None = None, timeout: float = 15.0):
        super().__init__(base_url, timeout)
        self.token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _post(self, endpoint: str, payload: dict, headers: dict | None = None) -> dict[str, Any]:
        """Make authenticated POST request."""
        url = f"{self.base_url}{endpoint}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers or self._headers())
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            return {
                "success": resp.status_code == 200,
                "status_code": resp.status_code,
                "data": resp.json() if resp.status_code == 200 else None,
                "error": resp.text[:500] if resp.status_code != 200 else None,
                "latency_ms": latency_ms,
                "endpoint": endpoint,
                "supplier": self.SUPPLIER_CODE,
            }
        except httpx.TimeoutException:
            return {"success": False, "error": "timeout", "endpoint": endpoint, "supplier": self.SUPPLIER_CODE, "latency_ms": round((time.monotonic() - start) * 1000, 1)}
        except httpx.ConnectError as e:
            return {"success": False, "error": f"connection_error: {e}", "endpoint": endpoint, "supplier": self.SUPPLIER_CODE}
        except Exception as e:
            logger.error(f"WTatil API error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "endpoint": endpoint, "supplier": self.SUPPLIER_CODE}

    # ─── Auth (unified interface) ──────────────────────────────────────
    async def authenticate(self, credentials: dict) -> dict[str, Any]:
        """Get auth token (24h validity)."""
        return await self.authenticate_static(
            self.base_url,
            credentials.get("application_secret_key", ""),
            credentials.get("username", ""),
            credentials.get("password", ""),
        )

    @staticmethod
    async def authenticate_static(base_url: str, secret_key: str, username: str, password: str) -> dict[str, Any]:
        """Static auth method for backward compat."""
        url = f"{base_url.rstrip('/')}/api/Auth/get-token-async"
        payload = {
            "ApplicationSecretKey": secret_key,
            "UserName": username,
            "Password": password,
        }
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token") or data.get("Token") or data.get("data", {}).get("token", "")
                return {"success": bool(token), "token": token, "data": data, "latency_ms": latency_ms}
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:500], "latency_ms": latency_ms}
        except Exception as e:
            return {"success": False, "error": str(e), "latency_ms": round((time.monotonic() - start) * 1000, 1)}

    # ─── Unified search interface ──────────────────────────────────────
    async def search_tours(self, request: dict) -> dict[str, Any]:
        """Search tours with unified interface."""
        agency_id = request.get("agency_id", 0)
        payload: dict[str, Any] = {
            "AgencyId": agency_id,
            "StartDate": request.get("start_date", ""),
            "EndDate": request.get("end_date", ""),
            "AdultCount": request.get("adults", request.get("adult_count", 2)),
            "ChildCount": request.get("children", request.get("child_count", 0)),
            "Detail": request.get("detail", 0),
        }
        if request.get("tour_id"):
            payload["TourId"] = request["tour_id"]
        if request.get("tour_area_id"):
            payload["TourAreaId"] = request["tour_area_id"]
        if request.get("tour_country_id"):
            payload["TourCountryId"] = request["tour_country_id"]
        if request.get("child_birth_dates"):
            payload["ChildBirthDates"] = request["child_birth_dates"]

        result = await self._post("/api/TourCatalog/search-tour-async", payload)
        if result["success"] and result.get("data"):
            tours = result["data"] if isinstance(result["data"], list) else result["data"].get("tours", result["data"].get("data", []))
            if isinstance(tours, list):
                products = [self.normalize_product(t, "tour") for t in tours[:50]]
            else:
                products = [self.normalize_product(result["data"], "tour")]
            result["products"] = products
            result["total"] = len(products)
        return result

    def normalize_product(self, raw: dict, product_type: str) -> dict[str, Any]:
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": product_type,
            "external_id": str(raw.get("TourId", raw.get("Id", raw.get("id", "")))),
            "name": raw.get("TourName", raw.get("Name", raw.get("name", ""))),
            "location": raw.get("AreaName", raw.get("CountryName", raw.get("location", ""))),
            "price": raw.get("Price", raw.get("MinPrice", raw.get("price", 0))),
            "currency": raw.get("CurrencyCode", raw.get("currency", "TRY")),
            "availability": True,
            "raw": raw,
        }

    # ─── Tour Catalog (legacy methods, still used by direct endpoints) ─
    async def get_all_tours(self, agency_id: int) -> dict[str, Any]:
        return await self._post("/api/TourCatalog/getall-tour-async", {"AgencyId": agency_id})

    async def search_tours_legacy(
        self, agency_id: int, start_date: str, end_date: str,
        adult_count: int = 2, child_count: int = 0,
        child_birth_dates: list[str] | None = None,
        tour_id: int | None = None, tour_area_id: int | None = None,
        tour_country_id: int | None = None, detail: int = 0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "AgencyId": agency_id, "StartDate": start_date, "EndDate": end_date,
            "AdultCount": adult_count, "ChildCount": child_count, "Detail": detail,
        }
        if tour_id:
            payload["TourId"] = tour_id
        if tour_area_id:
            payload["TourAreaId"] = tour_area_id
        if tour_country_id:
            payload["TourCountryId"] = tour_country_id
        if child_birth_dates:
            payload["ChildBirthDates"] = child_birth_dates
        return await self._post("/api/TourCatalog/search-tour-async", payload)

    # ─── Basket ───────────────────────────────────────────────────────
    async def add_basket_item(self, agency_id: int, reference_number: str, product_id: int,
                               product_type_id: int, product_period_id: int, price: str,
                               currency_code: str, customers: list[dict], billing_details: dict) -> dict[str, Any]:
        return await self._post("/api/Basket/add-basket-item-async", {
            "AgencyId": agency_id, "ReferenceNumber": reference_number,
            "ProductId": product_id, "ProductTypeId": product_type_id,
            "ProductPeriodId": product_period_id, "Price": price,
            "CurrencyCode": currency_code, "Customers": customers,
            "BillingDetails": billing_details,
        })

    async def get_basket(self, agency_id: int, basket_id: int) -> dict[str, Any]:
        return await self._post("/api/Basket/get-basket-by-id-async", {"AgencyId": agency_id, "Id": basket_id})

    async def delete_basket(self, agency_id: int, basket_id: int) -> dict[str, Any]:
        return await self._post("/api/Basket/delete-basket-by-id-async", {"AgencyId": agency_id, "Id": basket_id})

    async def delete_basket_item(self, agency_id: int, basket_id: int, basket_item_id: int) -> dict[str, Any]:
        return await self._post("/api/Basket/delete-basket-item-by-id-async", {
            "AgencyId": agency_id, "BasketId": basket_id, "BasketItemId": basket_item_id,
        })

    # ─── Booking (unified) ────────────────────────────────────────────
    async def create_booking(self, request: dict) -> dict[str, Any]:
        result = await self._post("/api/Booking/create-succeeded-booking-async", {
            "AgencyId": request.get("agency_id", 0),
            "BasketId": request.get("basket_id", 0),
            "TrackingNumber": request.get("tracking_number", ""),
            "Price": request.get("price", ""),
        })
        if result["success"] and result.get("data"):
            result["booking"] = self.normalize_booking(result["data"])
        return result

    async def cancel_booking(self, request: dict) -> dict[str, Any]:
        return await self._post("/api/BookingChangeRequest/create-booking-cancel-request-async", request)

    # ─── Booking extras ───────────────────────────────────────────────
    async def get_booking_states(self) -> dict[str, Any]:
        return await self._post("/api/Booking/getall-booking-state-async", {})

    async def add_booking_note(self, agency_id: int, booking_id: int, note: str) -> dict[str, Any]:
        return await self._post("/api/Booking/add-booking-note-async", {
            "AgencyId": agency_id, "BookingId": booking_id, "Note": note,
        })

    async def update_booking_note(self, note_id: int, agency_id: int, booking_id: int, note: str) -> dict[str, Any]:
        return await self._post("/api/Booking/update-booking-note-async", {
            "Id": note_id, "AgencyId": agency_id, "BookingId": booking_id, "Note": note,
        })

    # ─── Post-Sale ────────────────────────────────────────────────────
    async def change_tour_period(self, payload: dict) -> dict[str, Any]:
        return await self._post("/api/BookingChangeRequest/create-tour-period-change-request-async", payload)

    async def change_tour(self, payload: dict) -> dict[str, Any]:
        return await self._post("/api/BookingChangeRequest/create-tour-change-request-async", payload)

    async def add_additional_service(self, payload: dict) -> dict[str, Any]:
        return await self._post("/api/BookingChangeRequest/create-additional-service-add-request-async", payload)

    async def delete_additional_service(self, payload: dict) -> dict[str, Any]:
        return await self._post("/api/BookingChangeRequest/create-additional-service-delete-request-async", payload)

    async def cancel_service(self, payload: dict) -> dict[str, Any]:
        return await self._post("/api/BookingChangeRequest/create-service-cancel-request-async", payload)
