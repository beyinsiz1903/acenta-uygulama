from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from fastapi import Request

from app.utils import now_utc


def audit_snapshot(entity_type: str, doc: dict | None) -> dict | None:
    """PII-safe, entity-type based snapshot for audit before/after.

    Keeps only business-critical fields per entity_type; avoids leaking full docs.
    """
    if doc is None:
        return None

    # Helper to extract selected fields safely
    def pick(fields: list[str]) -> dict:
        out: dict[str, Any] = {}
        for f in fields:
            if f in doc and doc[f] is not None:
                out[f] = doc[f]
        return out

    et = (entity_type or "").lower()

    if et == "credit_profile":
        # credit profile snapshot
        return pick([
            "agency_id",
            "currency",
            "limit",
            "soft_limit",
            "payment_terms",
            "status",
            "updated_at",
            "updated_by",
        ])

    if et == "refund_case":
        # refund case snapshot
        snap: dict[str, Any] = {}
        snap.update(pick([
            "booking_id",
            "agency_id",
            "status",
            "currency",
            "reason",
            "decision",
            "decision_by_email",
            "decision_at",
            "updated_at",
        ]))
        requested = doc.get("requested") or {}
        computed = doc.get("computed") or {}
        approved = doc.get("approved") or {}
        snap["requested"] = {
            "amount": requested.get("amount"),
        }
        snap["computed"] = {
            "gross_sell": computed.get("gross_sell"),
            "penalty": computed.get("penalty"),
            "refundable": computed.get("refundable"),
            "basis": computed.get("basis"),
            "policy_ref": computed.get("policy_ref"),
        }
        snap["approved"] = {
            "amount": approved.get("amount"),
            "payment_reference": approved.get("payment_reference"),
        }
        return snap
    if et == "document":
        # document snapshot (no raw storage path to avoid leaking internals)
        snap: dict[str, Any] = {}
        snap.update(pick([
            "filename",
            "content_type",
            "size_bytes",
            "status",
            "created_at",
            "created_by_email",
        ]))
        storage = doc.get("storage") or {}
        snap["storage"] = {
            "provider": storage.get("provider"),
            "has_path": bool(storage.get("path")),
        }
    if et == "ops_task":
        snap: dict[str, Any] = {}
        snap.update(pick([
            "task_type",
            "title",
            "status",
            "priority",
            "due_at",
            "assignee_email",
            "entity_type",
            "entity_id",
            "booking_id",
            "updated_at",
        ]))
        return snap


        return snap



    if et == "pricing_rule":
        return pick([
            "code",
            "status",
            "priority",
            "scope",
            "action",
            "created_at",
            "updated_at",
            "created_by_email",
            "published_at",
            "published_by_email",
        ])

    if et == "partner":
        return pick([
            "name",
            "contact_email",
            "status",
            "default_markup_percent",
            "api_key_name",
            "linked_agency_id",
            "updated_at",
        ])

    if et == "b2b_marketplace_product":
        snap: dict[str, Any] = {}
        snap.update(pick([
            "partner_id",
            "product_id",
            "is_enabled",
            "commission_rate",
            "updated_at",
        ]))
        return snap

    # Fallback: keep nothing for unknown types
    return None


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
