"""Syroce Marketplace AGENT client.

Constructor takes an organization_id, loads the encrypted API key from DB,
decrypts it, and uses it as X-API-Key in all requests.

This is what powers the per-tenant proxy endpoints. Each call is scoped to
exactly one organization's marketplace credentials.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from app.services.syroce.crypto import decrypt_key
from app.services.syroce.errors import SyroceError

logger = logging.getLogger(__name__)


def _base_url() -> str:
    url = os.environ.get("SYROCE_BASE_URL", "").rstrip("/")
    if not url:
        raise SyroceError(500, "SYROCE_BASE_URL ortam değişkeni tanımlı değil.")
    return url


class SyroceAgentClient:
    """Per-organization Syroce client. Use `from_organization_id` to construct."""

    def __init__(self, *, organization_id: str, api_key: str, syroce_agency_id: Optional[str] = None):
        self.organization_id = organization_id
        self._api_key = api_key
        self.syroce_agency_id = syroce_agency_id

    @classmethod
    async def from_organization_id(cls, organization_id: str) -> "SyroceAgentClient":
        """Load the org's encrypted marketplace key from DB and build a client.

        Raises SyroceError(409) if the org has not been provisioned with Syroce.
        """
        from app.db import get_db
        db = await get_db()
        doc = await db.syroce_agencies.find_one({"organization_id": organization_id})
        if not doc:
            raise SyroceError(
                409,
                "Bu acenta henüz Syroce Marketplace'e kayıtlı değil. "
                "Yönetici panelinden 'Syroce'da Yeniden Senkronize Et' butonunu kullanın.",
            )
        if doc.get("syroce_status") != "active":
            raise SyroceError(
                409,
                f"Syroce Marketplace bağlantınız aktif değil (durum: {doc.get('syroce_status')}).",
            )
        ciphertext = doc.get("syroce_api_key_encrypted")
        if not ciphertext:
            raise SyroceError(
                409,
                "Syroce API anahtarı kayıtlı değil. Yöneticiden 'API Key'i Yenile' istemeniz gerekebilir.",
            )
        try:
            api_key = decrypt_key(ciphertext)
        except Exception as exc:
            raise SyroceError(500, str(exc)) from exc
        return cls(
            organization_id=organization_id,
            api_key=api_key,
            syroce_agency_id=doc.get("syroce_agency_id"),
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: float = 25.0,
    ) -> Dict[str, Any]:
        url = f"{_base_url()}{path}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(method, url, headers=self._headers(), params=params, json=json_body)
        except httpx.RequestError as exc:
            logger.warning("syroce agent network error org=%s path=%s err=%s", self.organization_id, path, exc)
            raise SyroceError(502, f"Syroce API erişilemedi: {exc}") from exc

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
                detail = f"Syroce API hatası ({resp.status_code})"
            raise SyroceError(resp.status_code, str(detail), data if isinstance(data, dict) else {})

        if not isinstance(data, dict):
            return {"data": data}
        return data

    # ── Public methods ──────────────────────────────────────────

    async def list_hotels(
        self,
        *,
        city: Optional[str] = None,
        country: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if city: params["city"] = city
        if country: params["country"] = country
        if q: params["q"] = q
        return await self._request("GET", "/listings", params=params or None)

    async def search_availability(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/search", json_body=payload)

    async def get_rates(self, *, tenant_id: str, room_type: str, check_in: str, check_out: str) -> Dict[str, Any]:
        return await self._request("GET", "/rates", params={
            "tenant_id": tenant_id,
            "room_type": room_type,
            "check_in": check_in,
            "check_out": check_out,
        })

    async def create_reservation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/reservations", json_body=payload, timeout=30.0)

    async def get_reservation(self, reservation_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/reservations/{reservation_id}")

    async def cancel_reservation(self, reservation_id: str, *, reason: str = "agency_request") -> Dict[str, Any]:
        return await self._request("DELETE", f"/reservations/{reservation_id}", params={"reason": reason})

    async def reconciliation(
        self, *, period_start: str, period_end: str, tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"period_start": period_start, "period_end": period_end}
        if tenant_id: params["tenant_id"] = tenant_id
        return await self._request("GET", "/reconciliation/agency", params=params)
