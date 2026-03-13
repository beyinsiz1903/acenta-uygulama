"""Base Supplier Adapter — Unified interface for all travel suppliers.

Every supplier adapter must implement this interface.
The aggregator uses these methods to fan-out searches and normalize results.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger("suppliers.base")


class SupplierAdapter(ABC):
    """Abstract base class for all supplier adapters."""

    SUPPLIER_CODE: str = ""
    PRODUCT_TYPES: list[str] = []  # e.g. ["hotel"], ["hotel","flight","tour"]

    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ─── Auth ──────────────────────────────────────────────────────────
    @abstractmethod
    async def authenticate(self, credentials: dict) -> dict[str, Any]:
        """Authenticate with the supplier and return token/session info.
        Returns: {"success": bool, "token": str|None, ...}
        """

    # ─── Search ────────────────────────────────────────────────────────
    async def search_hotels(self, request: dict) -> dict[str, Any]:
        """Search hotels. Override if supplier supports hotels."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE, "product_type": "hotel"}

    async def search_tours(self, request: dict) -> dict[str, Any]:
        """Search tours. Override if supplier supports tours."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE, "product_type": "tour"}

    async def search_flights(self, request: dict) -> dict[str, Any]:
        """Search flights. Override if supplier supports flights."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE, "product_type": "flight"}

    async def search_transfers(self, request: dict) -> dict[str, Any]:
        """Search transfers. Override if supplier supports transfers."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE, "product_type": "transfer"}

    async def search_activities(self, request: dict) -> dict[str, Any]:
        """Search activities. Override if supplier supports activities."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE, "product_type": "activity"}

    # ─── Availability / Pricing ────────────────────────────────────────
    async def get_availability(self, request: dict) -> dict[str, Any]:
        """Check real-time availability for a specific product."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE}

    # ─── Booking ───────────────────────────────────────────────────────
    async def create_booking(self, request: dict) -> dict[str, Any]:
        """Create a booking."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE}

    async def cancel_booking(self, request: dict) -> dict[str, Any]:
        """Cancel a booking."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE}

    async def get_booking_status(self, request: dict) -> dict[str, Any]:
        """Get booking status."""
        return {"supported": False, "supplier": self.SUPPLIER_CODE}

    # ─── Helpers ───────────────────────────────────────────────────────
    async def _post(self, endpoint: str, payload: dict, headers: dict | None = None) -> dict[str, Any]:
        """Make authenticated POST request with timing."""
        url = f"{self.base_url}{endpoint}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers or {})
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
            logger.error(f"{self.SUPPLIER_CODE} API error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "endpoint": endpoint, "supplier": self.SUPPLIER_CODE}

    async def _get(self, endpoint: str, params: dict | None = None, headers: dict | None = None) -> dict[str, Any]:
        """Make authenticated GET request with timing."""
        url = f"{self.base_url}{endpoint}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=headers or {})
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
            logger.error(f"{self.SUPPLIER_CODE} API error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "endpoint": endpoint, "supplier": self.SUPPLIER_CODE}

    def normalize_product(self, raw: dict, product_type: str) -> dict[str, Any]:
        """Normalize a supplier-specific product into the unified model.
        Override in each adapter for proper mapping.
        """
        return {
            "supplier": self.SUPPLIER_CODE,
            "product_type": product_type,
            "external_id": str(raw.get("id", "")),
            "name": raw.get("name", ""),
            "location": raw.get("location", ""),
            "price": raw.get("price", 0),
            "currency": raw.get("currency", "TRY"),
            "availability": raw.get("availability", True),
            "raw": raw,
        }

    def normalize_booking(self, raw: dict) -> dict[str, Any]:
        """Normalize a supplier booking into the unified model."""
        return {
            "supplier": self.SUPPLIER_CODE,
            "external_booking_id": str(raw.get("id", raw.get("booking_id", ""))),
            "status": raw.get("status", "unknown"),
            "price": raw.get("price", 0),
            "currency": raw.get("currency", "TRY"),
            "raw": raw,
        }
