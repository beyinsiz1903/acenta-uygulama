from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_roles
from app.db import get_db


router = APIRouter(prefix="/api/admin/funnel", tags=["admin_funnel"])


@router.get("/events")
async def list_funnel_events(
    correlation_id: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    channel: Optional[str] = Query(default=None),
    limit: int = Query(200, ge=1, le=500),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> List[Dict[str, Any]]:
    org_id = user["organization_id"]

    q: Dict[str, Any] = {"organization_id": org_id}
    if correlation_id:
        q["correlation_id"] = correlation_id
    if entity_id:
        q["entity_id"] = entity_id
    if channel:
        q["channel"] = channel

    cur = (
        db.funnel_events.find(q)
        .sort("created_at", 1)
        .limit(limit)
    )
    docs = await cur.to_list(length=limit)

    for d in docs:
        d["id"] = str(d.pop("_id"))

    return docs


@router.get("/summary")
async def funnel_summary(
    days: int = Query(7, ge=1, le=90),
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["super_admin", "admin", "ops"])),
) -> Dict[str, Any]:
    org_id = user["organization_id"]
    now = datetime.utcnow()
    since = now - timedelta(days=days)

    base_q = {"organization_id": org_id, "created_at": {"$gte": since}}

    # Aggregate by channel + event_name in a single query for efficiency
    pipeline = [
        {"$match": base_q},
        {
            "$group": {
                "_id": {"channel": "$channel", "event_name": "$event_name"},
                "count": {"$sum": 1},
            }
        },
    ]

    cur = db.funnel_events.aggregate(pipeline)
    rows = await cur.to_list(length=None)

    def _empty_bucket() -> Dict[str, Any]:
        return {
            "quote_count": 0,
            "checkout_started_count": 0,
            "booking_created_count": 0,
            "payment_succeeded_count": 0,
            "payment_failed_count": 0,
            "conversion": 0.0,
        }

    # Buckets: overall + per channel
    total = _empty_bucket()
    by_channel: Dict[str, Dict[str, Any]] = {
        "public": _empty_bucket(),
        "b2b": _empty_bucket(),
    }

    def _apply(bucket: Dict[str, Any], event_name: str, cnt: int) -> None:
        if event_name.endswith("quote.created"):
            bucket["quote_count"] += cnt
        elif event_name.endswith("checkout.started"):
            bucket["checkout_started_count"] += cnt
        elif event_name.endswith("booking.created"):
            bucket["booking_created_count"] += cnt
        elif event_name.endswith("payment.succeeded"):
            bucket["payment_succeeded_count"] += cnt
        elif event_name.endswith("payment.failed"):
            bucket["payment_failed_count"] += cnt

    for row in rows:
        ident = row.get("_id") or {}
        channel = ident.get("channel") or "unknown"
        event_name = ident.get("event_name") or ""
        cnt = int(row.get("count") or 0)

        # Apply to global totals
        _apply(total, event_name, cnt)

        # Apply to known channels
        if channel in by_channel:
            _apply(by_channel[channel], event_name, cnt)

    def _compute_conversion(bucket: Dict[str, Any]) -> None:
        qc = bucket["quote_count"]
        bc = bucket["booking_created_count"]
        bucket["conversion"] = (bc / qc) if qc > 0 else 0.0

    _compute_conversion(total)
    for ch in by_channel.values():
        _compute_conversion(ch)

    return {
        "days": days,
        "quote_count": total["quote_count"],
        "checkout_started_count": total["checkout_started_count"],
        "booking_created_count": total["booking_created_count"],
        "payment_succeeded_count": total["payment_succeeded_count"],
        "payment_failed_count": total["payment_failed_count"],
        "conversion": total["conversion"],
        "by_channel": by_channel,
    }
