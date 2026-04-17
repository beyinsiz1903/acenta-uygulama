"""Syroce Marketplace ADMIN client.

Sadece backend'in kullandığı, X-Marketplace-Admin-Token header'lı çağrılar.
Her organizasyonumuza karşılık PMS tarafında bir marketplace agency yaratıp,
RAW API key'i alıp DB'ye şifreli yazmak için kullanılır.

ASLA: raw key log'a yazılmamalı, response'ta UI'a dönmemeli.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from app.services.syroce.errors import SyroceError

logger = logging.getLogger(__name__)


def _base_url() -> str:
    url = os.environ.get("SYROCE_BASE_URL", "").rstrip("/")
    if not url:
        raise SyroceError(500, "SYROCE_BASE_URL ortam değişkeni tanımlı değil.")
    return url


def _admin_token() -> str:
    token = os.environ.get("SYROCE_MARKETPLACE_ADMIN_TOKEN", "").strip()
    if not token:
        raise SyroceError(500, "SYROCE_MARKETPLACE_ADMIN_TOKEN ortam değişkeni tanımlı değil.")
    return token


def _headers() -> Dict[str, str]:
    return {
        "X-Marketplace-Admin-Token": _admin_token(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _request(
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 25.0,
) -> Dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, headers=_headers(), json=json_body, params=params)
    except httpx.RequestError as exc:
        # Do not leak headers/keys
        logger.warning("syroce admin network error path=%s err=%s", path, exc)
        raise SyroceError(502, f"Syroce admin API erişilemedi: {exc}") from exc

    try:
        data = resp.json() if resp.content else {}
    except Exception:
        data = {}

    if resp.status_code >= 400:
        detail = ""
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("message") or data.get("error") or ""
            if isinstance(detail, dict):
                detail = detail.get("message") or str(detail)
        if not detail:
            detail = f"Syroce admin API hatası ({resp.status_code})"
        raise SyroceError(resp.status_code, str(detail), data if isinstance(data, dict) else {})

    if not isinstance(data, dict):
        return {"data": data}
    return data


# ─────────────────────────────────────────────────────────────────────
# Public admin operations
# ─────────────────────────────────────────────────────────────────────

async def create_syroce_agency(
    *,
    name: str,
    contact_email: str,
    contact_phone: str,
    country: str,
    default_commission_pct: float,
) -> Dict[str, Any]:
    """POST /admin/agencies → { agency_id, api_key (RAW!), warning, ... }

    RAW api_key sadece bu yanıtta gelir; çağıran şifrelemeli.
    """
    body = {
        "name": name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "country": country,
        "default_commission_pct": float(default_commission_pct),
    }
    return await _request("POST", "/admin/agencies", json_body=body)


async def regenerate_api_key(syroce_agency_id: str) -> Dict[str, Any]:
    """POST /admin/agencies/{id}/api-keys/regenerate → yeni RAW api_key"""
    return await _request("POST", f"/admin/agencies/{syroce_agency_id}/api-keys/regenerate")


async def disable_syroce_agency(syroce_agency_id: str) -> Dict[str, Any]:
    """DELETE /admin/agencies/{id}"""
    return await _request("DELETE", f"/admin/agencies/{syroce_agency_id}")
