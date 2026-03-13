"""WWTatil Tour API Adapter — Production-grade B2B integration.

Implements the full wwtatil.com Tour API flow:
  Auth → GetAll Tours → Search Tour → Add Basket → Create Booking

Per-agency credentials model: each agency provides their own wwtatil credentials.
Token caching per agency (24h validity).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("suppliers.wwtatil")


class WWTatilAdapter:
    """HTTP client for WWTatil Tour API.

    Usage:
        adapter = WWTatilAdapter(base_url, token)
        tours = await adapter.get_all_tours(agency_id)
        results = await adapter.search_tours(agency_id, params)
        basket = await adapter.add_basket_item(agency_id, item)
        booking = await adapter.create_booking(agency_id, basket_id, tracking, price)
    """

    def __init__(self, base_url: str, token: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    async def _post(self, endpoint: str, payload: dict) -> dict[str, Any]:
        """Make authenticated POST request."""
        url = f"{self.base_url}{endpoint}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
            latency_ms = round((time.monotonic() - start) * 1000, 1)

            return {
                "success": resp.status_code == 200,
                "status_code": resp.status_code,
                "data": resp.json() if resp.status_code == 200 else None,
                "error": resp.text[:500] if resp.status_code != 200 else None,
                "latency_ms": latency_ms,
                "endpoint": endpoint,
            }
        except httpx.TimeoutException:
            return {"success": False, "error": "timeout", "endpoint": endpoint, "latency_ms": round((time.monotonic() - start) * 1000, 1)}
        except httpx.ConnectError as e:
            return {"success": False, "error": f"connection_error: {e}", "endpoint": endpoint, "latency_ms": 0}
        except Exception as e:
            logger.error(f"WWTatil API error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "endpoint": endpoint, "latency_ms": 0}

    # ─── Auth ─────────────────────────────────────────────────────────────
    @staticmethod
    async def authenticate(base_url: str, secret_key: str, username: str, password: str) -> dict[str, Any]:
        """Get auth token (24h validity)."""
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

    # ─── Tour Catalog ─────────────────────────────────────────────────────
    async def get_all_tours(self, agency_id: int) -> dict[str, Any]:
        """Get all available tours."""
        return await self._post("/api/TourCatalog/getall-tour-async", {
            "AgencyId": agency_id,
        })

    async def search_tours(
        self,
        agency_id: int,
        start_date: str,
        end_date: str,
        adult_count: int = 2,
        child_count: int = 0,
        child_birth_dates: list[str] | None = None,
        tour_id: int | None = None,
        tour_area_id: int | None = None,
        tour_country_id: int | None = None,
        detail: int = 0,
    ) -> dict[str, Any]:
        """Search tours with pricing."""
        payload: dict[str, Any] = {
            "AgencyId": agency_id,
            "StartDate": start_date,
            "EndDate": end_date,
            "AdultCount": adult_count,
            "ChildCount": child_count,
            "Detail": detail,
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

    # ─── Basket ───────────────────────────────────────────────────────────
    async def add_basket_item(
        self,
        agency_id: int,
        reference_number: str,
        product_id: int,
        product_type_id: int,
        product_period_id: int,
        price: str,
        currency_code: str,
        customers: list[dict],
        billing_details: dict,
    ) -> dict[str, Any]:
        """Add item to basket (creates basket if TrackingNumber is new)."""
        return await self._post("/api/Basket/add-basket-item-async", {
            "AgencyId": agency_id,
            "ReferenceNumber": reference_number,
            "ProductId": product_id,
            "ProductTypeId": product_type_id,
            "ProductPeriodId": product_period_id,
            "Price": price,
            "CurrencyCode": currency_code,
            "Customers": customers,
            "BillingDetails": billing_details,
        })

    async def get_basket(self, agency_id: int, basket_id: int) -> dict[str, Any]:
        """Get basket by ID."""
        return await self._post("/api/Basket/get-basket-by-id-async", {
            "AgencyId": agency_id,
            "Id": basket_id,
        })

    async def delete_basket(self, agency_id: int, basket_id: int) -> dict[str, Any]:
        """Delete basket."""
        return await self._post("/api/Basket/delete-basket-by-id-async", {
            "AgencyId": agency_id,
            "Id": basket_id,
        })

    async def delete_basket_item(self, agency_id: int, basket_id: int, basket_item_id: int) -> dict[str, Any]:
        """Delete item from basket."""
        return await self._post("/api/Basket/delete-basket-item-by-id-async", {
            "AgencyId": agency_id,
            "BasketId": basket_id,
            "BasketItemId": basket_item_id,
        })

    # ─── Booking ──────────────────────────────────────────────────────────
    async def get_booking_states(self) -> dict[str, Any]:
        """Get all booking states."""
        return await self._post("/api/Booking/getall-booking-state-async", {})

    async def get_booking_cancel_types(self) -> dict[str, Any]:
        """Get all cancel types."""
        return await self._post("/api/Booking/getall-booking-cancel-type-async", {})

    async def get_payment_types(self) -> dict[str, Any]:
        """Get all payment types."""
        return await self._post("/api/Booking/getall-payment-type-async", {})

    async def create_booking(
        self,
        agency_id: int,
        basket_id: int,
        tracking_number: str,
        price: str,
    ) -> dict[str, Any]:
        """Create confirmed booking from basket."""
        return await self._post("/api/Booking/create-succeeded-booking-async", {
            "AgencyId": agency_id,
            "BasketId": basket_id,
            "TrackingNumber": tracking_number,
            "Price": price,
        })

    async def add_booking_note(self, agency_id: int, booking_id: int, note: str) -> dict[str, Any]:
        """Add note to booking."""
        return await self._post("/api/Booking/add-booking-note-async", {
            "AgencyId": agency_id,
            "BookingId": booking_id,
            "Note": note,
        })

    async def update_booking_note(self, note_id: int, agency_id: int, booking_id: int, note: str) -> dict[str, Any]:
        """Update booking note."""
        return await self._post("/api/Booking/update-booking-note-async", {
            "Id": note_id,
            "AgencyId": agency_id,
            "BookingId": booking_id,
            "Note": note,
        })

    # ─── Post-Sale Changes ────────────────────────────────────────────────
    async def cancel_booking(self, payload: dict) -> dict[str, Any]:
        """Request booking cancellation."""
        return await self._post("/api/BookingChangeRequest/create-booking-cancel-request-async", payload)

    async def change_tour_period(self, payload: dict) -> dict[str, Any]:
        """Request tour period change."""
        return await self._post("/api/BookingChangeRequest/create-tour-period-change-request-async", payload)

    async def change_tour(self, payload: dict) -> dict[str, Any]:
        """Request tour change."""
        return await self._post("/api/BookingChangeRequest/create-tour-change-request-async", payload)

    async def add_additional_service(self, payload: dict) -> dict[str, Any]:
        """Request additional service."""
        return await self._post("/api/BookingChangeRequest/create-additional-service-add-request-async", payload)

    async def delete_additional_service(self, payload: dict) -> dict[str, Any]:
        """Request service deletion."""
        return await self._post("/api/BookingChangeRequest/create-additional-service-delete-request-async", payload)

    async def cancel_service(self, payload: dict) -> dict[str, Any]:
        """Request service cancellation."""
        return await self._post("/api/BookingChangeRequest/create-service-cancel-request-async", payload)
