"""HotelsPro XML/REST API Adapter.

Supplier capability: Hotel
Auth: API-key based (X-Api-Key header)
Docs: https://developer.hotelspro.com/
"""
from __future__ import annotations

import logging
import time
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from .base_adapter import SupplierAdapter

logger = logging.getLogger("suppliers.hotelspro")

HOTELSPRO_SANDBOX = "https://sandbox-api.hotelspro.com/api/v2"
HOTELSPRO_PRODUCTION = "https://api.hotelspro.com/api/v2"


class HotelsProAdapter(SupplierAdapter):
    SUPPLIER_CODE = "hotelspro"
    PRODUCT_TYPES = ["hotel"]

    def __init__(
        self,
        base_url: str = HOTELSPRO_SANDBOX,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        super().__init__(base_url, timeout)
        self.api_key = api_key

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            h["Authorization"] = f"ApiKey {self.api_key}"
            h["X-Api-Key"] = self.api_key
        return h

    def _xml_headers(self) -> dict:
        h = {
            "Content-Type": "application/xml",
            "Accept": "application/xml",
        }
        if self.api_key:
            h["Authorization"] = f"ApiKey {self.api_key}"
            h["X-Api-Key"] = self.api_key
        return h

    async def authenticate(self, credentials: dict) -> dict[str, Any]:
        api_key = credentials.get("api_key", "")
        if not api_key:
            return {"success": False, "error": "api_key required"}

        self.api_key = api_key
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/hotel-availability-list",
                    params={"pax": "2", "checkin": "2099-01-01", "checkout": "2099-01-02", "client_nationality": "TR"},
                    headers=self._headers(),
                )
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            if resp.status_code == 200:
                return {"success": True, "api_key": api_key[:8] + "***", "latency_ms": latency_ms}
            if resp.status_code in (401, 403):
                return {"success": False, "error": "invalid_api_key", "latency_ms": latency_ms}
            return {"success": False, "error": f"status_{resp.status_code}", "latency_ms": latency_ms}
        except Exception as e:
            logger.exception("HotelsPro auth check failed")
            return {"success": False, "error": str(e)}

    async def search_hotels(self, request: dict) -> dict[str, Any]:
        checkin = request.get("checkin", "")
        checkout = request.get("checkout", "")
        pax = request.get("pax", "2")
        destination = request.get("destination", "")
        nationality = request.get("client_nationality", "TR")

        if not checkin or not checkout:
            return {"success": False, "error": "checkin and checkout required", "supplier": self.SUPPLIER_CODE}

        params = {
            "pax": str(pax),
            "checkin": checkin,
            "checkout": checkout,
            "client_nationality": nationality,
        }
        if destination:
            params["destination_code"] = destination

        result = await self._get("/hotel-availability-list", params=params, headers=self._headers())
        if not result.get("success"):
            return result

        raw_hotels = result.get("data", {}).get("results", [])
        normalized = [self._normalize_hotel(h) for h in raw_hotels]
        return {
            "success": True,
            "supplier": self.SUPPLIER_CODE,
            "product_type": "hotel",
            "total": len(normalized),
            "results": normalized,
            "latency_ms": result.get("latency_ms"),
        }

    async def get_availability(self, request: dict) -> dict[str, Any]:
        hotel_code = request.get("hotel_code", "")
        checkin = request.get("checkin", "")
        checkout = request.get("checkout", "")
        pax = request.get("pax", "2")
        nationality = request.get("client_nationality", "TR")

        if not hotel_code or not checkin or not checkout:
            return {"success": False, "error": "hotel_code, checkin and checkout required"}

        params = {
            "hotel_code": hotel_code,
            "pax": str(pax),
            "checkin": checkin,
            "checkout": checkout,
            "client_nationality": nationality,
        }
        result = await self._get("/hotel-availability", params=params, headers=self._headers())
        if not result.get("success"):
            return result

        rooms = result.get("data", {}).get("results", [])
        return {
            "success": True,
            "supplier": self.SUPPLIER_CODE,
            "hotel_code": hotel_code,
            "rooms": rooms,
            "latency_ms": result.get("latency_ms"),
        }

    async def create_booking(self, request: dict) -> dict[str, Any]:
        payload = {
            "hotel_code": request.get("hotel_code", ""),
            "offer_id": request.get("offer_id", ""),
            "pax": request.get("pax", []),
            "client_ref": request.get("client_ref", ""),
            "notes": request.get("notes", ""),
        }
        result = await self._post("/bookings", payload=payload, headers=self._headers())
        if not result.get("success"):
            return result

        booking_data = result.get("data", {})
        return {
            "success": True,
            "supplier": self.SUPPLIER_CODE,
            "booking": self.normalize_booking(booking_data),
            "latency_ms": result.get("latency_ms"),
        }

    async def cancel_booking(self, request: dict) -> dict[str, Any]:
        booking_code = request.get("booking_code", "")
        if not booking_code:
            return {"success": False, "error": "booking_code required"}

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.delete(
                    f"{self.base_url}/bookings/{booking_code}",
                    headers=self._headers(),
                )
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            if resp.status_code in (200, 204):
                return {"success": True, "booking_code": booking_code, "status": "cancelled", "latency_ms": latency_ms}
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:500], "latency_ms": latency_ms}
        except Exception as e:
            logger.exception("HotelsPro cancel booking failed")
            return {"success": False, "error": str(e)}

    async def get_booking_status(self, request: dict) -> dict[str, Any]:
        booking_code = request.get("booking_code", "")
        if not booking_code:
            return {"success": False, "error": "booking_code required"}

        result = await self._get(f"/bookings/{booking_code}", headers=self._headers())
        if not result.get("success"):
            return result
        return {
            "success": True,
            "supplier": self.SUPPLIER_CODE,
            "booking": self.normalize_booking(result.get("data", {})),
            "latency_ms": result.get("latency_ms"),
        }

    async def search_hotels_xml(self, xml_payload: str) -> dict[str, Any]:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/hotel-availability-list",
                    content=xml_payload,
                    headers=self._xml_headers(),
                )
            latency_ms = round((time.monotonic() - start) * 1000, 1)

            if resp.status_code != 200:
                return {"success": False, "status_code": resp.status_code, "error": resp.text[:500], "latency_ms": latency_ms}

            hotels = self._parse_xml_hotels(resp.text)
            return {
                "success": True,
                "supplier": self.SUPPLIER_CODE,
                "product_type": "hotel",
                "total": len(hotels),
                "results": hotels,
                "latency_ms": latency_ms,
                "format": "xml",
            }
        except Exception as e:
            logger.exception("HotelsPro XML search failed")
            return {"success": False, "error": str(e)}

    def build_search_xml(
        self,
        checkin: str,
        checkout: str,
        pax: str = "2",
        destination_code: str = "",
        nationality: str = "TR",
    ) -> str:
        root = ET.Element("AvailabilityRequest")
        ET.SubElement(root, "CheckIn").text = checkin
        ET.SubElement(root, "CheckOut").text = checkout
        ET.SubElement(root, "Pax").text = str(pax)
        ET.SubElement(root, "ClientNationality").text = nationality
        if destination_code:
            ET.SubElement(root, "DestinationCode").text = destination_code
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def _parse_xml_hotels(self, xml_text: str) -> list[dict]:
        results = []
        try:
            root = ET.fromstring(xml_text)
            for hotel_el in root.iter("Hotel"):
                results.append({
                    "supplier": self.SUPPLIER_CODE,
                    "product_type": "hotel",
                    "external_id": hotel_el.findtext("Code", ""),
                    "name": hotel_el.findtext("Name", ""),
                    "location": hotel_el.findtext("Destination", ""),
                    "star_rating": int(hotel_el.findtext("Stars", "0") or "0"),
                    "price": float(hotel_el.findtext("MinPrice", "0") or "0"),
                    "currency": hotel_el.findtext("Currency", "EUR"),
                    "availability": True,
                })
        except ET.ParseError:
            logger.exception("Failed to parse HotelsPro XML response")
        return results

    def _normalize_hotel(self, raw: dict) -> dict[str, Any]:
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": "hotel",
            "external_id": raw.get("code", raw.get("hotel_code", "")),
            "name": raw.get("name", raw.get("hotel_name", "")),
            "location": raw.get("destination", {}).get("name", "") if isinstance(raw.get("destination"), dict) else raw.get("destination", ""),
            "star_rating": raw.get("stars", 0),
            "price": float(raw.get("min_price", 0)),
            "currency": raw.get("currency", "EUR"),
            "availability": True,
            "thumbnail": raw.get("thumbnail", ""),
            "raw": raw,
        }
