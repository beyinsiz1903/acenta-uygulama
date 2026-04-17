"""Async HTTP client for TourVisio (San TSG) — multi-product API.

All endpoints are POST with JSON `{header, body}` envelope. Auth is Login-based:
the client logs in once, caches the bearer token until `expiresOn`, and reuses
it across calls. The client exposes:

  * `request(path, body)` — generic POST returning the unwrapped `body` dict.
  * Typed convenience wrappers for the most common endpoints (autocomplete,
    pricesearch, product info, booking lifecycle, lookups).

Higher-level orchestration lives in the proxy router.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.services.tourvisio.errors import TourVisioError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0
LOGIN_PATH = "/api/authenticationservice/login"


def _env(name: str) -> str:
    val = os.environ.get(name) or ""
    if not val:
        raise TourVisioError(
            500,
            f"{name} ortam değişkeni tanımlı değil. Replit Secrets üzerinden ekleyin.",
        )
    return val


class _TokenCache:
    """Process-wide cache for the TourVisio bearer token."""

    def __init__(self) -> None:
        self.token: Optional[str] = None
        self.expires_at: Optional[datetime] = None
        self.lock = asyncio.Lock()

    def is_valid(self) -> bool:
        if not self.token or not self.expires_at:
            return False
        # 60s safety margin
        return datetime.now(timezone.utc) < (self.expires_at - timedelta(seconds=60))


_token_cache = _TokenCache()


class TourVisioClient:
    """Async wrapper around the TourVisio multi-product API."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        agency: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._base_url = (base_url or _env("TOURVISIO_BASE_URL")).rstrip("/")
        self._agency = agency or _env("TOURVISIO_AGENCY")
        self._user = user or _env("TOURVISIO_USER")
        self._password = password or _env("TOURVISIO_PASSWORD")
        self._timeout = timeout

    # ───────────────── Auth ─────────────────

    async def _login(self) -> str:
        """Perform Login and update the shared token cache. Returns the token."""
        url = f"{self._base_url}{LOGIN_PATH}"
        body = {
            "header": None,
            "body": {
                "Agency": self._agency,
                "User": self._user,
                "Password": self._password,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as cli:
                resp = await cli.post(
                    url,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "Accept": "application/json",
                    },
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise TourVisioError(504, "TourVisio login timeout") from exc
        except httpx.HTTPError as exc:
            raise TourVisioError(502, f"TourVisio login bağlantı hatası: {exc}") from exc

        if resp.status_code >= 400:
            raise TourVisioError(resp.status_code, f"TourVisio login HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            data = resp.json()
        except Exception as exc:
            raise TourVisioError(502, f"TourVisio login geçersiz JSON: {exc}") from exc

        header = data.get("header") or {}
        body_out = data.get("body") or {}
        if header.get("success") is False:
            msgs = header.get("messages") or []
            msg = msgs[0].get("message") if msgs else "TourVisio login başarısız"
            raise TourVisioError(401, msg, payload=data)

        token = body_out.get("token") or body_out.get("Token")
        expires_on = body_out.get("expiresOn") or body_out.get("ExpiresOn")
        if not token:
            raise TourVisioError(502, "TourVisio login token döndürmedi", payload=data)

        # Parse expiresOn (ISO format) — fall back to 8h if unparseable
        expires_at: datetime
        try:
            if expires_on:
                # tolerate 'Z' suffix and missing tz
                clean = expires_on.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(clean)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                expires_at = parsed
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
        except Exception:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=8)

        _token_cache.token = token
        _token_cache.expires_at = expires_at
        logger.info("TourVisio login OK; token cached until %s", expires_at.isoformat())
        return token

    async def _get_token(self) -> str:
        if _token_cache.is_valid() and _token_cache.token:
            return _token_cache.token
        async with _token_cache.lock:
            if _token_cache.is_valid() and _token_cache.token:
                return _token_cache.token
            return await self._login()

    # ───────────────── Generic POST ─────────────────

    async def request(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST to `path` with `{header: {token}, body}` envelope; return unwrapped `body`.

        Raises `TourVisioError` on transport errors, HTTP >= 400, or `header.success=false`.
        """
        if not path.startswith("/"):
            path = "/" + path
        token = await self._get_token()
        url = f"{self._base_url}{path}"
        envelope = {"header": {"token": token}, "body": body or {}}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as cli:
                resp = await cli.post(
                    url,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "Accept": "application/json",
                    },
                    json=envelope,
                )
        except httpx.TimeoutException as exc:
            raise TourVisioError(504, f"TourVisio yanıt vermedi (timeout): {path}") from exc
        except httpx.HTTPError as exc:
            raise TourVisioError(502, f"TourVisio bağlantı hatası: {exc}") from exc

        # Token expired mid-call? Force re-login once.
        if resp.status_code in (401, 403):
            _token_cache.token = None
            _token_cache.expires_at = None
            token = await self._get_token()
            envelope["header"]["token"] = token
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as cli:
                    resp = await cli.post(url, headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "Accept": "application/json",
                    }, json=envelope)
            except httpx.HTTPError as exc:
                raise TourVisioError(502, f"TourVisio bağlantı hatası (retry): {exc}") from exc

        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except Exception:
                payload = {"raw": resp.text[:500]}
            raise TourVisioError(resp.status_code, f"TourVisio HTTP {resp.status_code}", payload=payload)

        try:
            data = resp.json()
        except Exception as exc:
            raise TourVisioError(502, f"TourVisio geçersiz JSON: {exc}") from exc

        header = data.get("header") or {}
        if header.get("success") is False:
            msgs = header.get("messages") or []
            msg = (msgs[0].get("message") if msgs else None) or "TourVisio başarısız yanıt"
            raise TourVisioError(400, msg, payload=data)

        return data.get("body") or {}

    # ───────────────── Lookups (commonservice) ─────────────────

    async def get_payment_types(self, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return await self.request("/api/commonservice/getpaymenttypes", body or {})

    async def get_transportations(self, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return await self.request("/api/commonservice/gettransportations", body or {})

    async def get_exchange_rates(self, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return await self.request("/api/commonservice/exchangerates", body or {})

    # ───────────────── Search (productservice) ─────────────────

    async def autocomplete(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Generic autocomplete (cities/hotels/airports/etc) — caller supplies productType."""
        return await self.request("/api/productservice/getarrivalautocomplete", body)

    async def departure_autocomplete(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getdepartureautocomplete", body)

    async def get_check_in_dates(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getcheckindates", body)

    async def price_search(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Universal price search — works for all product types via `productType` field.

        ProductType IDs:
          1=Holiday Package, 2=Hotel, 3=Flight, 4=Excursion, 5=Transfer,
          6=Tour Culture Package, 13=Dynamic Package, 14=Rent a Car
        """
        return await self.request("/api/productservice/pricesearch", body)

    async def get_product_info(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Hotel/product detail by offer/product ID."""
        return await self.request("/api/productservice/getproductinfo", body)

    async def get_offer_details(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getofferdetails", body)

    async def get_fare_rules(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Flight fare rules."""
        return await self.request("/api/productservice/getfarerules", body)

    # ───────────────── Booking (bookingservice) ─────────────────

    async def begin_transaction(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/bookingservice/begintransaction", body)

    async def set_reservation_info(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/bookingservice/setreservationinfo", body)

    async def commit_transaction(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/bookingservice/committransaction", body)

    async def get_reservation_detail(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/bookingservice/getreservationdetail", body)

    # ───────────────── Cancellation ─────────────────

    async def get_cancellation_penalty(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/bookingservice/getcancellationpenalty", body)

    async def cancel_reservation(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/bookingservice/cancelreservation", body)

    # ───────────────── Token cache helpers ─────────────────

    @staticmethod
    def clear_cached_token() -> None:
        _token_cache.token = None
        _token_cache.expires_at = None

    @staticmethod
    def cached_token_status() -> Dict[str, Any]:
        return {
            "has_token": bool(_token_cache.token),
            "expires_at": _token_cache.expires_at.isoformat() if _token_cache.expires_at else None,
            "valid": _token_cache.is_valid(),
        }
