"""Public inbound webhook receiver (PMS -> agency), Scenario B.

This router is mounted WITHOUT auth (the PMS authenticates itself by signing the
request body with the secret we registered). It must:
  - verify the HMAC signature (fail-closed when missing/invalid),
  - return a fast 2xx, and
  - record the event for asynchronous processing.

The path is intentionally namespaced and unguessable-by-role so it never collides
with the JWT-gated admin surface.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.syroce_b2b import webhooks

logger = logging.getLogger("syroce_b2b.inbound")

INBOUND_WEBHOOK_PATH = "/api/b2b-agency/webhook"

router = APIRouter(tags=["syroce-b2b-inbound"])


@router.post(INBOUND_WEBHOOK_PATH)
async def receive_webhook(request: Request) -> JSONResponse:
    body = await request.body()
    headers = dict(request.headers)

    if not await webhooks.verify_signature(headers, body):
        # Fail-closed: reject anything we cannot authenticate. 401 is deliberate
        # and leaks nothing about why (missing secret vs. bad signature).
        return JSONResponse(status_code=401, content={"ok": False})

    try:
        payload: Dict[str, Any] = json.loads(body) if body else {}
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {"_raw": payload}

    event_type = payload.get("event") or payload.get("event_type") or payload.get("type")
    try:
        await webhooks.record_event(event_type, payload)
    except Exception as exc:
        # Returning 5xx asks the PMS to retry (its retry+DLQ handles delivery).
        logger.warning("syroce_b2b inbound webhook record failed: %s", exc)
        return JSONResponse(status_code=503, content={"ok": False})

    return JSONResponse(status_code=202, content={"ok": True})


__all__ = ["router", "INBOUND_WEBHOOK_PATH"]
