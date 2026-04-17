"""Async HTTP client for TourVisio (San TSG) — multi-product API.

Per-tenant: each instance is constructed with the calling agency's own
credentials (base_url, agency, user, password). Credentials are NOT read from
environment variables — they are loaded by the router from the encrypted
`supplier_credentials` collection (see `app.domain.suppliers.supplier_credentials_service`).

Auth is Login-based: the client logs in once, caches the bearer token until
`expiresOn` in a process-wide dict keyed by `(base_url, agency, user)`, and
reuses it across calls. The cache is shared across requests but partitioned
by tenant so different agencies never share tokens.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import httpx

from app.services.tourvisio.errors import TourVisioError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0
LOGIN_PATH = "/api/authenticationservice/login"


class _TokenEntry:
    __slots__ = ("token", "expires_at", "lock")

    def __init__(self) -> None:
        self.token: Optional[str] = None
        self.expires_at: Optional[datetime] = None
        self.lock = asyncio.Lock()

    def is_valid(self) -> bool:
        if not self.token or not self.expires_at:
            return False
        return datetime.now(timezone.utc) < (self.expires_at - timedelta(seconds=60))


# process-wide cache keyed by (base_url, agency, user)
_TOKENS: Dict[Tuple[str, str, str], _TokenEntry] = {}
_TOKENS_LOCK = asyncio.Lock()


async def _get_entry(key: Tuple[str, str, str]) -> _TokenEntry:
    entry = _TOKENS.get(key)
    if entry is not None:
        return entry
    async with _TOKENS_LOCK:
        entry = _TOKENS.get(key)
        if entry is None:
            entry = _TokenEntry()
            _TOKENS[key] = entry
        return entry


class TourVisioClient:
    """Async wrapper around the TourVisio multi-product API (per-tenant)."""

    def __init__(
        self,
        *,
        base_url: str,
        agency: str,
        user: str,
        password: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        if not (base_url and agency and user and password):
            raise TourVisioError(400, "TourVisio credentials eksik (base_url/agency/user/password).")
        self._base_url = base_url.rstrip("/")
        self._agency = agency
        self._user = user
        self._password = password
        self._timeout = timeout
        self._cache_key = (self._base_url, self._agency, self._user)

    # ───────────────── Auth ─────────────────

    async def _login(self, entry: _TokenEntry) -> str:
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
                resp = await cli.post(url, headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                }, json=body)
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

        try:
            if expires_on:
                clean = str(expires_on).replace("Z", "+00:00")
                parsed = datetime.fromisoformat(clean)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                expires_at = parsed
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
        except Exception:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=8)

        entry.token = token
        entry.expires_at = expires_at
        logger.info("TourVisio login OK (agency=%s); token cached until %s",
                    self._agency, expires_at.isoformat())
        return token

    async def _get_token(self) -> str:
        entry = await _get_entry(self._cache_key)
        if entry.is_valid() and entry.token:
            return entry.token
        async with entry.lock:
            if entry.is_valid() and entry.token:
                return entry.token
            return await self._login(entry)

    async def login(self) -> Dict[str, Any]:
        """Force a fresh Login (clears cache for this tenant first)."""
        entry = await _get_entry(self._cache_key)
        async with entry.lock:
            entry.token = None
            entry.expires_at = None
            await self._login(entry)
        return self.token_status()

    def token_status(self) -> Dict[str, Any]:
        entry = _TOKENS.get(self._cache_key)
        return {
            "has_token": bool(entry and entry.token),
            "expires_at": entry.expires_at.isoformat() if entry and entry.expires_at else None,
            "valid": bool(entry and entry.is_valid()),
        }

    def clear_token(self) -> None:
        entry = _TOKENS.get(self._cache_key)
        if entry:
            entry.token = None
            entry.expires_at = None

    # ───────────────── Generic POST ─────────────────

    async def request(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path
        token = await self._get_token()
        url = f"{self._base_url}{path}"
        envelope = {"header": {"token": token}, "body": body or {}}
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as cli:
                resp = await cli.post(url, headers=headers, json=envelope)
        except httpx.TimeoutException as exc:
            raise TourVisioError(504, f"TourVisio yanıt vermedi (timeout): {path}") from exc
        except httpx.HTTPError as exc:
            raise TourVisioError(502, f"TourVisio bağlantı hatası: {exc}") from exc

        # Token expired mid-call? Force re-login once.
        if resp.status_code in (401, 403):
            self.clear_token()
            token = await self._get_token()
            envelope["header"]["token"] = token
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as cli:
                    resp = await cli.post(url, headers=headers, json=envelope)
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
        return await self.request("/api/productservice/getarrivalautocomplete", body)

    async def departure_autocomplete(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getdepartureautocomplete", body)

    async def get_check_in_dates(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getcheckindates", body)

    async def price_search(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Universal price search — works for all product types via `productType` field."""
        return await self.request("/api/productservice/pricesearch", body)

    async def get_product_info(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getproductinfo", body)

    async def get_offer_details(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getofferdetails", body)

    async def get_fare_rules(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("/api/productservice/getfarerules", body)

    # ───────────────── Booking ─────────────────

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

    # ───────────────── Class-level cache helpers ─────────────────

    @staticmethod
    def clear_all_cached_tokens() -> None:
        _TOKENS.clear()
