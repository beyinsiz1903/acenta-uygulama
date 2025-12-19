from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from fastapi import Request

from app.utils import now_utc


def _safe_json(v: Any, max_len: int = 2000) -> Any:
    """Make sure audit payload stays light; truncate long strings."""
    if v is None:
        return None
    if isinstance(v, (int, float, bool)):
        return v
    if isinstance(v, str):
        return v if len(v) <= max_len else v[:max_len] + "…"
    if isinstance(v, list):
        return [_safe_json(x, max_len=max_len) for x in v][:200]
    if isinstance(v, dict):
        out: dict[str, Any] = {}
        for k, val in list(v.items())[:200]:
            out[str(k)] = _safe_json(val, max_len=max_len)
        return out

    # fallback to string
    s = str(v)
    return s if len(s) <= max_len else s[:max_len] + "…"


def shallow_diff(before: Optional[dict[str, Any]], after: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Return only changed fields (top-level) as {field: {before, after}}.

    We keep this intentionally shallow to avoid huge audit docs.
    """
    b = before or {}
    a = after or {}

    keys = set(b.keys()) | set(a.keys())
    diff: dict[str, Any] = {}
    for k in keys:
        if k == "_id":
            continue
        bv = b.get(k)
        av = a.get(k)
        if bv != av:
            diff[k] = {"before": _safe_json(bv), "after": _safe_json(av)}
    return diff


def _get_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # first ip
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


async def write_audit_log(
    db,
    *,
    organization_id: str,
    actor: dict[str, Any],
    request: Request,
    action: str,
    target_type: str,
    target_id: str,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Persist audit log.

    actor expected: {actor_type, actor_id, email, roles}
    origin captures ip/user-agent/path/app_version and optional request-id.
    """

    origin = {
        "ip": _get_ip(request),
        "user_agent": request.headers.get("user-agent", ""),
        "path": str(request.url.path),
        "method": request.method,
        "app_version": request.headers.get("x-app-version", ""),
        "request_id": request.headers.get("x-request-id", ""),
    }

    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "actor": {
            "actor_type": actor.get("actor_type", "user"),
            "actor_id": actor.get("actor_id") or actor.get("id") or actor.get("email"),
            "email": actor.get("email"),
            "roles": actor.get("roles") or [],
        },
        "origin": origin,
        "action": action,
        "target": {"type": target_type, "id": target_id},
        "diff": shallow_diff(before, after),
        "meta": _safe_json(meta or {}),
        "created_at": now_utc(),
    }

    # Ensure serializable (especially meta)
    try:
        json.dumps(doc, default=str)
    except Exception:
        doc["meta"] = {"note": "meta_unserializable"}

    await db.audit_logs.insert_one(doc)
