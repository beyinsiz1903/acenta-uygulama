"""Syroce PMS B2B integration (agency/client side) — Scenario B.

Connects THIS agency-automation app to the authoritative Syroce PMS B2B backend
as a channel-manager-style client. Security is **X-API-Key only**; the key is
obtained through an approval-gated onboarding flow and stored encrypted.

Components:
  - ``onboarding``      — approval-gated connect-request flow that retrieves the
                          one-time API key (persisted, encrypted).
  - ``client`` (Ch. A)  — REST: availability / rates / reservations / folio +
                          webhook-subscription management. X-API-Key on every
                          call; stable Idempotency-Key on POST /reservations.
  - ``webhooks`` + ``webhook_routes`` — inbound signed-webhook receiver.
  - ``polling``         — periodic REST polling of availability/rates into a local
                          table (last-write-wins). The Scenario B real-time path.
  - ``connection_store``— encrypted, single-doc credential/connection store.

Scenario A's Redis-Streams ARI consumer is intentionally absent: a separate Replit
project cannot reach the PMS Redis. The PMS is authoritative; on conflict it wins.
All write paths are fail-closed and idempotent. No secret is ever logged/returned.
"""
from __future__ import annotations

from app.services.syroce_b2b.config import SyroceB2BConfig, get_b2b_config
from app.services.syroce_b2b.errors import SyroceB2BError

__all__ = ["SyroceB2BConfig", "get_b2b_config", "SyroceB2BError"]
