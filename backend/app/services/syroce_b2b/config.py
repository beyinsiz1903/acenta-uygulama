"""Environment-driven configuration for the Syroce PMS B2B integration.

All values come from Replit secrets / environment variables and are read
lazily so the app boots cleanly even when the integration is not yet
configured. Secrets are NEVER logged or returned to clients.

    SYROCE_B2B_BASE_URL   REST base, e.g. https://<pms-domain>/api/b2b
    SYROCE_AGENCY_API_KEY agency key sent as X-API-Key on every REST call
    SYROCE_TENANT_ID      PMS tenant id (stream scope + rate lookups)
    SYROCE_AGENCY_ID      this agency's id (stream scope)
    SYROCE_REDIS_URL      private-network Redis URL for the ARI stream
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _clean(name: str) -> str:
    return (os.environ.get(name) or "").strip()


@dataclass(frozen=True)
class SyroceB2BConfig:
    base_url: str
    api_key: str
    tenant_id: str
    agency_id: str
    redis_url: str

    @property
    def rest_ready(self) -> bool:
        """REST (Channel A) needs base URL + API key + identity."""
        return bool(self.base_url and self.api_key and self.tenant_id and self.agency_id)

    @property
    def stream_ready(self) -> bool:
        """ARI stream (Channel B) needs Redis URL + identity."""
        return bool(self.redis_url and self.tenant_id and self.agency_id)

    @property
    def stream_name(self) -> str:
        """The single stream this agency is allowed to read."""
        return f"b2b:tenant:{self.tenant_id}:agency:{self.agency_id}:ari:v1"


def get_b2b_config() -> SyroceB2BConfig:
    """Build the config from the current environment (cheap; call freely)."""
    return SyroceB2BConfig(
        base_url=_clean("SYROCE_B2B_BASE_URL").rstrip("/"),
        api_key=_clean("SYROCE_AGENCY_API_KEY"),
        tenant_id=_clean("SYROCE_TENANT_ID"),
        agency_id=_clean("SYROCE_AGENCY_ID"),
        redis_url=_clean("SYROCE_REDIS_URL"),
    )


def public_status() -> dict:
    """Non-sensitive status summary safe to return to admins/clients.

    Reports only booleans and the stream name (which contains tenant/agency
    ids, not secrets). The API key and Redis URL are never exposed.
    """
    cfg = get_b2b_config()
    return {
        "rest_ready": cfg.rest_ready,
        "stream_ready": cfg.stream_ready,
        "base_url_configured": bool(cfg.base_url),
        "api_key_configured": bool(cfg.api_key),
        "tenant_id_configured": bool(cfg.tenant_id),
        "agency_id_configured": bool(cfg.agency_id),
        "redis_url_configured": bool(cfg.redis_url),
        "stream_name": cfg.stream_name if (cfg.tenant_id and cfg.agency_id) else None,
    }


__all__ = ["SyroceB2BConfig", "get_b2b_config", "public_status"]
