from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crm", tags=["crm-timeline"])


# ─── Activity feed (deal or customer scoped) ──────────────────────
@router.get("/activity")
async def get_activity(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(require_roles(["agency_agent", "super_admin", "tenant_admin"])),
):
    """Return recent audit events for a deal or customer."""
    org_id = user.get("organization_id")
    q = {"organization_id": org_id}

    if entity_type and entity_id:
        q["$or"] = [
            {"target.type": entity_type, "target.id": entity_id},
            {"meta.entity_type": entity_type, "meta.entity_id": entity_id},
            {"meta.deal_id": entity_id} if entity_type == "deal" else {},
        ]
        q["$or"] = [f for f in q["$or"] if f]

    cursor = db.audit_logs.find(q).sort("created_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id", ""))
        items.append(doc)
    return {"items": items, "total": len(items)}


# ─── Customer timeline (aggregated) ──────────────────────────────
@router.get("/customers/{customer_id}/timeline")
async def get_customer_timeline(
    customer_id: str,
    limit: int = Query(50, ge=1, le=200),
    filter_type: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(require_roles(["agency_agent", "super_admin", "tenant_admin"])),
):
    """Aggregated timeline for a customer: reservations, payments, notes, deals, tasks."""
    org_id = user.get("organization_id")
    events = []

    # 1) Notes on this customer
    if not filter_type or filter_type == "notes":
        notes = await db.crm_notes.find(
            {"organization_id": org_id, "entity_type": "customer", "entity_id": customer_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        for n in notes:
            events.append({
                "ts": n.get("created_at"),
                "type": "note",
                "title": "Not eklendi",
                "subtitle": (n.get("content") or "")[:120],
                "entity_id": n.get("id"),
                "created_by": n.get("created_by_email", ""),
            })

    # 2) Deals linked to this customer
    deals = await db.crm_deals.find(
        {"organization_id": org_id, "customer_id": customer_id}, {"_id": 0}
    ).sort("updated_at", -1).limit(50).to_list(50)
    deal_ids = [d["id"] for d in deals if d.get("id")]

    if not filter_type or filter_type == "deals":
        for d in deals:
            events.append({
                "ts": d.get("created_at"),
                "type": "deal",
                "title": f"Deal: {d.get('title', '')}",
                "subtitle": f"Stage: {d.get('stage', '')} | {d.get('amount', 0)} {d.get('currency', '')}",
                "entity_id": d.get("id"),
                "link": f"/app/crm/pipeline?deal={d.get('id')}",
            })

    # 3) Tasks linked to this customer or their deals
    if not filter_type or filter_type == "tasks":
        task_q = {"organization_id": org_id, "$or": [{"related_type": "customer", "related_id": customer_id}]}
        if deal_ids:
            task_q["$or"].append({"related_type": "deal", "related_id": {"$in": deal_ids}})
        tasks = await db.crm_tasks.find(task_q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        for t in tasks:
            events.append({
                "ts": t.get("created_at"),
                "type": "task",
                "title": f"Gorev: {t.get('title', '')}",
                "subtitle": f"Durum: {t.get('status', '')}",
                "entity_id": t.get("id"),
            })

    # 4) Notes on deals
    if deal_ids and (not filter_type or filter_type == "notes"):
        deal_notes = await db.crm_notes.find(
            {"organization_id": org_id, "entity_type": "deal", "entity_id": {"$in": deal_ids}},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        for n in deal_notes:
            events.append({
                "ts": n.get("created_at"),
                "type": "note",
                "title": "Deal notu",
                "subtitle": (n.get("content") or "")[:120],
                "entity_id": n.get("id"),
            })

    # 5) Reservations
    if not filter_type or filter_type == "reservations":
        reservations = await db.reservations.find(
            {"organization_id": org_id, "customer_id": customer_id}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        for r in reservations:
            events.append({
                "ts": r.get("created_at"),
                "type": "reservation",
                "title": f"Rezervasyon: {r.get('status', '')}",
                "subtitle": f"{r.get('total', 0)} {r.get('currency', 'TRY')}",
                "entity_id": str(r.get("_id", r.get("id", ""))),
            })

    # 6) Payments
    if not filter_type or filter_type == "payments":
        payments = await db.webpos_payments.find(
            {"organization_id": org_id, "customer_id": customer_id}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        for p in payments:
            events.append({
                "ts": p.get("created_at"),
                "type": "payment",
                "title": f"Odeme: {p.get('status', '')}",
                "subtitle": f"{p.get('amount', 0)} {p.get('currency', 'TRY')}",
                "entity_id": str(p.get("_id", "")),
            })

    # Sort all by ts desc
    events.sort(key=lambda e: e.get("ts") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    events = events[:limit]

    return {"items": events, "total": len(events), "customer_id": customer_id}
