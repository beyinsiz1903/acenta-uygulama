"""Environment-driven configuration for the Syroce PMS B2B integration (Scenario B).

Scenario B (this app's default): the agency runs in a SEPARATE Replit project.
Security is **X-API-Key only** (no mTLS / IP-allowlist). Real-time updates use a
**webhook subscription + REST polling** — the PMS Redis is NOT reachable, so the
Redis-Streams ARI path (Scenario A) is intentionally absent here.

Only the two non-secret, deployment-level values come from the environment:

    SYROCE_B2B_BASE_URL   REST base, e.g. https://<pms-domain>/api/b2b
    SYROCE_TENANT_ID      PMS tenant (hotel) id, known out-of-band (informational)

The agency ``api_key`` and ``agency_id`` are NOT pre-provisioned secrets: they are
obtained at runtime through the approval-gated onboarding flow and persisted
(encrypted) in the connection store. ``SYROCE_AGENCY_API_KEY`` is still honoured
as an optional fallback (useful for testing / Scenario A), but the canonical
source is the connection store. Secrets are NEVER logged or returned to clients.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _clean(name: str) -> str:
    return (os.environ.get(name) or "").strip()


@dataclass(frozen=True)
class SyroceB2BConfig:
    base_url: str
    tenant_id: str
    api_key_env: str  # optional env fallback only; DB store is canonical

    @property
    def base_ready(self) -> bool:
        """The PMS REST base must be configured before anything can connect."""
        return bool(self.base_url)


def get_b2b_config() -> SyroceB2BConfig:
    """Build the (env-level) config from the current environment (cheap)."""
    return SyroceB2BConfig(
        base_url=_clean("SYROCE_B2B_BASE_URL").rstrip("/"),
        tenant_id=_clean("SYROCE_TENANT_ID"),
        api_key_env=_clean("SYROCE_AGENCY_API_KEY"),
    )


__all__ = ["SyroceB2BConfig", "get_b2b_config"]
