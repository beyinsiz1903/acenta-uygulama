"""Onboarding — approval-gated connection & API-key acquisition (Scenario B).

The hotel hands the agency two out-of-band values: the hotel id (tenant_id, only
informational here) and a one-time **connect code**. The connect code is
low-privilege: it can only create a connect request and poll its status — it can
NOT mint a key.

Flow (locked contract):
  1. POST /connect-requests  (header X-Connect-Code) → 201 returns request_id +
     request_token ONCE. Both MUST be persisted; without them status cannot be
     polled and the key cannot be retrieved. A repeat with the same
     ``agency_platform_request_id`` is idempotent and does NOT echo the token.
  2. GET /connect-requests/{request_id} (headers X-Connect-Code + X-Request-Token)
     → pending | rejected | approved(+api_key once). The raw api_key is returned
     only on the FIRST successful poll after approval, then nulled server-side.
  3. Lost-token / rotation recovery is hotel-initiated (see contract §0 step 3).

All secrets (connect code, request_token, api_key) are fail-closed and NEVER
logged. On ambiguity we raise rather than assume success.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.services.syroce_b2b import connection_store as store
from app.services.syroce_b2b.config import get_b2b_config
from app.services.syroce_b2b.errors import SyroceB2BError

logger = logging.getLogger("syroce_b2b.onboarding")

_TIMEOUT = 20.0


def _base_url() -> str:
    cfg = get_b2b_config()
    if not cfg.base_ready:
        raise SyroceB2BError(
            503,
            "Syroce PMS B2B taban adresi yapılandırılmamış (SYROCE_B2B_BASE_URL eksik).",
            code="not_configured",
            retryable=False,
        )
    return cfg.base_url


def _extract_detail(data: Any, status: int) -> str:
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            return err.get("message") or err.get("code") or f"Syroce PMS hatası ({status})"
        for k in ("detail", "message", "reason"):
            v = data.get(k)
            if isinstance(v, str) and v:
                return v
    return f"Syroce PMS hatası ({status})"


async def create_connect_request(
    *,
    connect_code: str,
    agency_name: str,
    agency_platform_request_id: str,
    contact_name: str = "",
    contact_email: str = "",
    contact_phone: str = "",
    note: str = "",
    external_agency_id: str = "",
    requested_scopes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Step 1 — create a connect request and persist request_id + request_token.

    Returns a NON-SECRET summary (status, request_id, idempotent flag). The raw
    request_token is persisted (encrypted) but never returned to the caller.
    """
    if not connect_code:
        raise SyroceB2BError(400, "Bağlantı kodu (connect code) gerekli.", code="missing_connect_code", retryable=False)
    if not agency_name:
        raise SyroceB2BError(422, "agency_name zorunludur.", code="missing_agency_name", retryable=False)

    scopes = requested_scopes or ["booking_engine", "webhooks"]
    body = {
        "agency_name": agency_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "note": note,
        "external_agency_id": external_agency_id,
        "agency_platform_request_id": agency_platform_request_id,
        "requested_scopes": scopes,
    }
    url = f"{_base_url()}/connect-requests"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
            resp = await http.post(url, headers={"X-Connect-Code": connect_code}, json=body)
    except httpx.TimeoutException as exc:
        raise SyroceB2BError(504, f"Syroce PMS zaman aşımı: {exc}", code="timeout") from exc
    except httpx.RequestError as exc:
        raise SyroceB2BError(502, f"Syroce PMS erişilemedi: {exc}", code="unreachable") from exc

    try:
        data: Any = resp.json() if resp.content else {}
    except ValueError:
        data = {}
    data = data if isinstance(data, dict) else {}

    if resp.status_code == 401:
        # Uniform 401 — no tenant existence oracle.
        raise SyroceB2BError(401, "Geçersiz veya eksik bağlantı kodu.", code="invalid_connect_code", retryable=False)
    if resp.status_code >= 400:
        raise SyroceB2BError(resp.status_code, _extract_detail(data, resp.status_code), payload=data, retryable=resp.status_code >= 500)

    # Idempotent repeat: no request_id/request_token echoed — keep whatever we stored.
    if data.get("idempotent") and not data.get("request_token"):
        return {
            "idempotent": True,
            "status": data.get("status"),
            "message": data.get("message") or "Bağlantı isteği zaten mevcut (idempotent).",
        }

    request_id = data.get("request_id")
    request_token = data.get("request_token")
    if not request_id or not request_token:
        # Fail-closed: a fresh 201 MUST carry both, otherwise we can never poll.
        raise SyroceB2BError(
            502,
            "Syroce PMS beklenen request_id/request_token alanlarını döndürmedi.",
            code="bad_connect_response",
            retryable=False,
        )

    await store.save_pending_request(
        request_id=request_id,
        request_token=request_token,
        agency_name=agency_name,
        scopes=scopes,
    )
    logger.info("syroce_b2b onboarding: connect request created (request_id stored).")
    return {
        "idempotent": False,
        "status": data.get("status") or "pending",
        "request_id": request_id,
        "message": "Bağlantı isteği oluşturuldu. Onay bekleniyor.",
    }


async def poll_connect_request(*, connect_code: str) -> Dict[str, Any]:
    """Step 2 — poll status; on first approved poll, retrieve & store the api_key.

    Returns a NON-SECRET summary. The raw api_key is persisted (encrypted) and
    never returned to the caller.
    """
    if not connect_code:
        raise SyroceB2BError(400, "Bağlantı kodu (connect code) gerekli.", code="missing_connect_code", retryable=False)

    doc = await store.public_view()
    request_id = doc.get("request_id")
    request_token = await store.get_request_token()
    if not request_id or not request_token:
        raise SyroceB2BError(
            409,
            "Saklı bağlantı isteği yok. Önce 'Bağlantı isteği oluştur' adımını çalıştırın.",
            code="no_pending_request",
            retryable=False,
        )

    url = f"{_base_url()}/connect-requests/{request_id}"
    headers = {"X-Connect-Code": connect_code, "X-Request-Token": request_token}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
            resp = await http.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise SyroceB2BError(504, f"Syroce PMS zaman aşımı: {exc}", code="timeout") from exc
    except httpx.RequestError as exc:
        raise SyroceB2BError(502, f"Syroce PMS erişilemedi: {exc}", code="unreachable") from exc

    try:
        data: Any = resp.json() if resp.content else {}
    except ValueError:
        data = {}
    data = data if isinstance(data, dict) else {}

    if resp.status_code == 401:
        raise SyroceB2BError(
            401,
            "Geçersiz istek doğrulaması (connect code / request token).",
            code="invalid_request_auth",
            retryable=False,
        )
    if resp.status_code >= 400:
        raise SyroceB2BError(resp.status_code, _extract_detail(data, resp.status_code), payload=data, retryable=resp.status_code >= 500)

    status = (data.get("status") or "").lower()

    if status == "rejected":
        await store.mark_rejected(data.get("reason"))
        return {"status": "rejected", "reason": data.get("reason")}

    if status == "pending":
        return {"status": "pending", "message": data.get("message") or "Onay bekleniyor."}

    if status == "approved":
        api_key = data.get("api_key")
        if api_key:
            await store.save_api_key(
                api_key=api_key,
                agency_id=data.get("agency_id"),
                scopes=data.get("scopes") or [],
                key_prefix=data.get("key_prefix"),
            )
            logger.info("syroce_b2b onboarding: api_key retrieved and stored (connected).")
            return {
                "status": "connected",
                "agency_id": data.get("agency_id"),
                "scopes": data.get("scopes") or [],
                "key_prefix": data.get("key_prefix"),
                "message": "API key tek seferlik alındı ve güvenli şekilde saklandı.",
            }
        # Approved but key not available (already retrieved / delivery expired).
        await store.mark_approved_pending_key()
        return {
            "status": "approved",
            "key_available": False,
            "reason": data.get("reason"),
            "message": "Onaylandı fakat API key alınamadı (zaten çekilmiş veya süresi geçmiş).",
        }

    return {"status": status or "unknown", "raw": data}


__all__ = ["create_connect_request", "poll_connect_request"]
