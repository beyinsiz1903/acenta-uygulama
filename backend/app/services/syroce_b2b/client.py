"""Channel A — Syroce PMS B2B REST client (agency side).

Contract-locked. Base URL = ``SYROCE_B2B_BASE_URL``; dates are ``YYYY-MM-DD``.
Every request carries ``X-API-Key``. ``POST /reservations`` additionally carries
a client-generated ``Idempotency-Key`` (UUID) that is REUSED across retries for
the same logical reservation.

Idempotency / retry semantics (client side):
  - same key + same body          -> PMS replays the original response.
  - same key + different body      -> 409 (permanent; surfaced to caller).
  - same key currently processing  -> 429 + Retry-After:N -> wait N, retry SAME key.
  - business 4xx (401/402/403/409/422) -> permanent; retry would replay it.
  - unexpected 5xx                 -> transient; retry SAME key with backoff.

Fail-closed: on ambiguity (network error after sending, exhausted retries) we
RAISE rather than assume success. Because the Idempotency-Key is stable, a later
retry / reconciliation against the PMS converges safely. No secret is logged.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

from app.services.syroce_b2b.config import SyroceB2BConfig, get_b2b_config
from app.services.syroce_b2b.errors import PERMANENT_STATUS, SyroceB2BError

logger = logging.getLogger("syroce_b2b.client")

# Retry budget for transient failures (429 in-flight + 5xx). Kept small and
# bounded so a write path can never hang indefinitely.
_MAX_ATTEMPTS = 5
_DEFAULT_RETRY_AFTER = 2.0  # seconds, per contract (429 -> Retry-After:2)
_MAX_RETRY_AFTER = 30.0     # clamp a hostile/huge Retry-After
_BACKOFF_BASE = 0.5         # 5xx backoff base (exponential)
_BACKOFF_CAP = 8.0


class SyroceB2BClient:
    """Stateless REST client bound to the env-configured agency identity."""

    def __init__(self, config: Optional[SyroceB2BConfig] = None, *, timeout: float = 25.0):
        self._cfg = config or get_b2b_config()
        self._timeout = timeout

    # ── internals ────────────────────────────────────────────────

    def _require_ready(self) -> SyroceB2BConfig:
        cfg = self._cfg
        if not cfg.rest_ready:
            # Fail-closed: never silently no-op a missing configuration.
            raise SyroceB2BError(
                503,
                "Syroce PMS B2B bağlantısı yapılandırılmamış "
                "(SYROCE_B2B_BASE_URL / SYROCE_AGENCY_API_KEY / "
                "SYROCE_TENANT_ID / SYROCE_AGENCY_ID eksik).",
                code="not_configured",
                retryable=False,
            )
        return cfg

    def _headers(self, *, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "X-API-Key": self._cfg.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def _parse_retry_after(resp: httpx.Response) -> float:
        raw = resp.headers.get("Retry-After")
        if raw:
            try:
                return max(0.0, min(float(raw), _MAX_RETRY_AFTER))
            except (TypeError, ValueError):
                pass
        return _DEFAULT_RETRY_AFTER

    @staticmethod
    def _extract_detail(data: Any, status: int) -> str:
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict):
                return err.get("message") or err.get("code") or f"Syroce PMS hatası ({status})"
            detail = data.get("detail") or data.get("message") or data.get("error")
            if isinstance(detail, str) and detail:
                return detail
        return f"Syroce PMS hatası ({status})"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        cfg = self._require_ready()
        url = f"{cfg.base_url}{path}"
        attempt = 0
        last_exc: Optional[SyroceB2BError] = None

        while attempt < _MAX_ATTEMPTS:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as http:
                    resp = await http.request(
                        method,
                        url,
                        headers=self._headers(idempotency_key=idempotency_key),
                        params=params,
                        json=json_body,
                    )
            except httpx.TimeoutException as exc:
                # Sent but no response: ambiguous. Safe to retry SAME key (GET is
                # idempotent; POST is protected by the stable Idempotency-Key).
                last_exc = SyroceB2BError(504, f"Syroce PMS zaman aşımı: {exc}", code="timeout")
                logger.warning("syroce_b2b timeout method=%s path=%s attempt=%d", method, path, attempt)
                await asyncio.sleep(self._backoff(attempt))
                continue
            except httpx.RequestError as exc:
                last_exc = SyroceB2BError(502, f"Syroce PMS erişilemedi: {exc}", code="unreachable")
                logger.warning("syroce_b2b network error method=%s path=%s attempt=%d", method, path, attempt)
                await asyncio.sleep(self._backoff(attempt))
                continue

            try:
                data: Any = resp.json() if resp.content else {}
            except ValueError:
                data = {}

            if resp.status_code < 400:
                return data if isinstance(data, dict) else {"data": data}

            status = resp.status_code

            # 429: in-flight. Wait Retry-After then retry with the SAME key.
            if status == 429:
                delay = self._parse_retry_after(resp)
                last_exc = SyroceB2BError(429, "İşlem hâlâ sürüyor, tekrar denenecek.", code="in_flight")
                logger.info("syroce_b2b 429 in-flight path=%s retry_after=%.1f attempt=%d", path, delay, attempt)
                await asyncio.sleep(delay)
                continue

            detail = self._extract_detail(data, status)
            payload = data if isinstance(data, dict) else {}

            # Permanent business errors: do not retry — a retry replays them.
            if status in PERMANENT_STATUS:
                raise SyroceB2BError(status, detail, payload=payload, retryable=False)

            # Unexpected 5xx: transient, retry with the SAME key.
            if status >= 500:
                last_exc = SyroceB2BError(status, detail, payload=payload, retryable=True)
                logger.warning("syroce_b2b 5xx path=%s status=%d attempt=%d", path, status, attempt)
                await asyncio.sleep(self._backoff(attempt))
                continue

            # Any other 4xx we did not special-case: treat as permanent.
            raise SyroceB2BError(status, detail, payload=payload, retryable=False)

        # Exhausted retries on a transient condition -> fail-closed.
        raise last_exc or SyroceB2BError(
            504, "Syroce PMS yanıt vermedi (deneme limiti aşıldı).", code="exhausted", retryable=True
        )

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(_BACKOFF_CAP, _BACKOFF_BASE * (2 ** (attempt - 1)))

    # ── Channel A endpoints ──────────────────────────────────────

    async def get_availability(
        self, *, check_in: str, check_out: str, room_type: Optional[str] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"check_in": check_in, "check_out": check_out}
        if room_type:
            params["room_type"] = room_type
        return await self._request("GET", "/availability", params=params)

    async def get_rates(
        self, *, start_date: str, end_date: str, room_type: Optional[str] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        if room_type:
            params["room_type"] = room_type
        return await self._request("GET", "/rates", params=params)

    async def create_reservation(
        self, body: Dict[str, Any], *, idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """POST /reservations with a stable client-generated Idempotency-Key.

        Pass ``idempotency_key`` to reuse a previously persisted key (e.g. when
        re-driving an uncertain attempt). Otherwise a fresh UUID is generated.
        """
        key = idempotency_key or str(uuid.uuid4())
        return await self._request("POST", "/reservations", json_body=body, idempotency_key=key)

    async def list_reservations(
        self,
        *,
        status: Optional[str] = None,
        check_in_from: Optional[str] = None,
        check_in_to: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": max(1, min(int(limit), 500))}  # contract: limit <= 500
        if status:
            params["status"] = status
        if check_in_from:
            params["check_in_from"] = check_in_from
        if check_in_to:
            params["check_in_to"] = check_in_to
        return await self._request("GET", "/reservations", params=params)

    async def get_reservation(self, reservation_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/reservations/{reservation_id}")

    async def cancel_reservation(self, reservation_id: str) -> Dict[str, Any]:
        return await self._request("PUT", f"/reservations/{reservation_id}/cancel")


__all__ = ["SyroceB2BClient"]
