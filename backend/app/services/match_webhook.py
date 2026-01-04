from __future__ import annotations

from datetime import datetime
from typing import Any, Tuple
import hashlib
import hmac
import json

import httpx

from app.utils import now_utc


async def send_match_alert_webhook(
    *,
    organization_id: str,
    webhook_url: str,
    webhook_secret: str | None,
    timeout_ms: int,
    payload: dict[str, Any],
) -> tuple[bool, int | None, str | None, str | None]:
    """Send a match.alert webhook.

    Returns: (ok, http_status, response_snippet, error)
    """

    timeout = timeout_ms / 1000.0 if timeout_ms and timeout_ms > 0 else 4.0
    body = json.dumps(payload, default=str).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Syroce-Event": payload.get("event", "match.alert"),
        "X-Syroce-Org": organization_id,
    }

    if webhook_secret:
        sig = hmac.new(webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers["X-Syroce-Signature"] = f"sha256={sig}"

    http_status: int | None = None
    snippet: str | None = None
    error: str | None = None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(webhook_url, content=body, headers=headers)
        http_status = resp.status_code
        text = resp.text or ""
        snippet = text[:300]
        ok = 200 <= http_status < 300
        if not ok:
            error = f"Non-2xx webhook status: {http_status}"
        return ok, http_status, snippet, error
    except Exception as e:  # pragma: no cover
        error = str(e)
        return False, http_status, snippet, error
