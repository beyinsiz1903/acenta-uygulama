"""Syroce PMS B2B integration (agency/client side).

This is the contract-locked, single-agency integration that connects THIS
agency-automation app to the authoritative Syroce PMS B2B backend.

Two channels:
  - Channel A (REST): synchronous availability/rates/reservations via
    ``client.SyroceB2BClient`` — X-API-Key on every call, client-generated
    Idempotency-Key on POST /reservations, full error-code + retry semantics.
  - Channel B (Redis Streams): real-time ARI (availability/rate/restriction)
    consumed from ``b2b:tenant:{TENANT}:agency:{AGENCY}:ari:v1`` via a consumer
    group, applied idempotently (last-write-wins by created_at).

The PMS is authoritative; on any conflict the PMS wins. All write paths are
fail-closed and idempotent. No secret is ever logged or returned to clients.
"""
from __future__ import annotations

from app.services.syroce_b2b.config import SyroceB2BConfig, get_b2b_config
from app.services.syroce_b2b.errors import SyroceB2BError

__all__ = ["SyroceB2BConfig", "get_b2b_config", "SyroceB2BError"]
