"""Syroce PMS Marketplace v1 client.

Acenta uygulamasının PMS Marketplace API'siyle konuşmasını sağlar.
Bütün isteklerde X-API-Key header'ı kullanılır.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class SyroceMarketplaceError(Exception):
    """Marketplace API hatası — http_status ve detail içerir."""

    def __init__(self, http_status: int, detail: str, payload: Optional[Dict[str, Any]] = None):
        self.http_status = http_status
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"[{http_status}] {detail}")


def _base_url() -> str:
    url = os.environ.get("SYROCE_MARKETPLACE_BASE_URL", "").rstrip("/")
    if not url:
        raise SyroceMarketplaceError(
            500,
            "SYROCE_MARKETPLACE_BASE_URL ortam değişkeni tanımlı değil.",
        )
    return url


def _api_key() -> str:
    key = os.environ.get("SYROCE_MARKETPLACE_API_KEY", "")
    if not key:
        raise SyroceMarketplaceError(
            500,
            "SYROCE_MARKETPLACE_API_KEY ortam değişkeni tanımlı değil.",
        )
    return key


def _headers() -> Dict[str, str]:
    return {
        "X-API-Key": _api_key(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _request(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=_headers(),
            )
    except httpx.RequestError as exc:
        logger.warning("syroce marketplace network error: %s", exc)
        raise SyroceMarketplaceError(
            502,
            f"Marketplace API'sine bağlanılamadı: {exc}",
        ) from exc

    # Try to parse JSON regardless of status
    try:
        data = resp.json() if resp.content else {}
    except Exception:
        data = {}

    if resp.status_code >= 400:
        detail = ""
        if isinstance(data, dict):
            detail = (
                data.get("detail")
                or data.get("message")
                or data.get("error")
                or ""
            )
            if isinstance(detail, dict):
                detail = detail.get("message") or str(detail)
        if not detail:
            detail = f"Marketplace API hatası ({resp.status_code})"
        raise SyroceMarketplaceError(resp.status_code, str(detail), data if isinstance(data, dict) else {})

    if not isinstance(data, dict):
        return {"data": data}
    return data


# ─────────────────────────────────────────────────────────────────────
# Public client functions — endpoint'lere birebir uyar
# ─────────────────────────────────────────────────────────────────────

async def list_hotels(
    *,
    city: Optional[str] = None,
    country: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """GET /listings"""
    params: Dict[str, Any] = {}
    if city:
        params["city"] = city
    if country:
        params["country"] = country
    if q:
        params["q"] = q
    return await _request("GET", "/listings", params=params or None)


async def search_availability(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST /search

    payload: { check_in, check_out, adults, children, city?, country?, q?, max_price?, room_type? }
    """
    return await _request("POST", "/search", json_body=payload)


async def get_rates(
    *,
    tenant_id: str,
    room_type: str,
    check_in: str,
    check_out: str,
) -> Dict[str, Any]:
    """GET /rates"""
    return await _request(
        "GET",
        "/rates",
        params={
            "tenant_id": tenant_id,
            "room_type": room_type,
            "check_in": check_in,
            "check_out": check_out,
        },
    )


async def create_reservation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST /reservations

    Zorunlu: tenant_id, room_type, check_in, check_out, guest_name,
             guest_email, guest_phone, adults, external_reference
    Opsiyonel: children, special_requests, total_amount

    NOT: total_amount gönderildiğinde server fiyatı ile ±0.50 toleransla karşılaştırılır.
    """
    return await _request("POST", "/reservations", json_body=payload, timeout=30.0)


async def get_reservation(reservation_id: str) -> Dict[str, Any]:
    """GET /reservations/{id}"""
    return await _request("GET", f"/reservations/{reservation_id}")


async def cancel_reservation(
    reservation_id: str,
    *,
    reason: str = "agency_request",
) -> Dict[str, Any]:
    """DELETE /reservations/{id}?reason=..."""
    return await _request(
        "DELETE",
        f"/reservations/{reservation_id}",
        params={"reason": reason},
    )


async def reconciliation_agency(
    *,
    period_start: str,
    period_end: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """GET /reconciliation/agency"""
    params: Dict[str, Any] = {
        "period_start": period_start,
        "period_end": period_end,
    }
    if tenant_id:
        params["tenant_id"] = tenant_id
    return await _request("GET", "/reconciliation/agency", params=params)
