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

    async def _count(event_name: str) -> int:
        return await db.funnel_events.count_documents({**base_q, "event_name": event_name})

    quote_count = await _count("public.quote.created") + await _count("b2b.quote.created")
    checkout_started_count = await _count("public.checkout.started") + await _count("b2b.checkout.started")
    booking_created_count = await _count("public.booking.created") + await _count("b2b.booking.created")
    payment_succeeded_count = await _count("public.payment.succeeded") + await _count("b2b.payment.succeeded")
    payment_failed_count = await _count("public.payment.failed") + await _count("b2b.payment.failed")

    conversion = (booking_created_count / quote_count) if quote_count > 0 else 0.0

    return {
        "days": days,
        "quote_count": quote_count,
        "checkout_started_count": checkout_started_count,
        "booking_created_count": booking_created_count,
        "payment_succeeded_count": payment_succeeded_count,
        "payment_failed_count": payment_failed_count,
        "conversion": conversion,
    }
