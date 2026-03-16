"""Settlement Workflow Service — Phase 2B Workflow & Ops.

Manages settlement run lifecycle transitions:
  draft -> pending_approval -> approved -> paid
                            -> rejected
Also handles adding/removing entries from draft runs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db import get_db

VALID_TRANSITIONS = {
    "draft": ["pending_approval"],
    "pending_approval": ["approved", "rejected"],
    "approved": ["paid"],
    "rejected": ["draft"],
    "paid": [],
    "partially_reconciled": ["reconciled"],
    "reconciled": [],
}


async def create_settlement_draft(
    org_id: str,
    run_type: str,
    entity_id: str,
    entity_name: str,
    period_start: str,
    period_end: str,
    currency: str = "EUR",
    notes: Optional[str] = None,
) -> dict:
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    count = await db.settlement_runs.count_documents({"org_id": org_id})
    run_id = f"SR-{count + 1:03d}"

    doc = {
        "run_id": run_id,
        "org_id": org_id,
        "status": "draft",
        "run_type": run_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "total_amount": 0,
        "currency": currency,
        "entries_count": 0,
        "period_start": period_start,
        "period_end": period_end,
        "created_at": now,
        "approved_at": None,
        "paid_at": None,
        "rejected_at": None,
        "notes": notes or "",
        "history": [{"action": "created", "timestamp": now, "actor": "system"}],
    }
    await db.settlement_runs.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def transition_settlement(
    org_id: str, run_id: str, target_status: str, actor: str = "admin", reason: Optional[str] = None
) -> dict:
    db = await get_db()
    run = await db.settlement_runs.find_one({"org_id": org_id, "run_id": run_id}, {"_id": 0})
    if not run:
        return {"error": "Settlement run not found", "status_code": 404}

    current = run["status"]
    if target_status not in VALID_TRANSITIONS.get(current, []):
        return {
            "error": f"Invalid transition: {current} -> {target_status}. Allowed: {VALID_TRANSITIONS.get(current, [])}",
            "status_code": 400,
        }

    now = datetime.now(timezone.utc).isoformat()
    update: dict = {"$set": {"status": target_status}}
    history_entry = {"action": target_status, "timestamp": now, "actor": actor}
    if reason:
        history_entry["reason"] = reason

    if target_status == "approved":
        update["$set"]["approved_at"] = now
    elif target_status == "paid":
        update["$set"]["paid_at"] = now
    elif target_status == "rejected":
        update["$set"]["rejected_at"] = now

    update["$push"] = {"history": history_entry}

    await db.settlement_runs.update_one({"org_id": org_id, "run_id": run_id}, update)

    updated = await db.settlement_runs.find_one({"org_id": org_id, "run_id": run_id}, {"_id": 0})
    return updated


async def add_entries_to_draft(org_id: str, run_id: str, entry_ids: list[str]) -> dict:
    db = await get_db()
    run = await db.settlement_runs.find_one({"org_id": org_id, "run_id": run_id}, {"_id": 0})
    if not run:
        return {"error": "Settlement run not found", "status_code": 404}
    if run["status"] != "draft":
        return {"error": "Entries can only be added to draft runs", "status_code": 400}

    result = await db.ledger_entries.update_many(
        {"org_id": org_id, "entry_id": {"$in": entry_ids}, "settlement_run_id": None},
        {"$set": {"settlement_run_id": run_id}},
    )
    linked_count = result.modified_count

    entries = await db.ledger_entries.find(
        {"org_id": org_id, "settlement_run_id": run_id}, {"_id": 0}
    ).to_list(length=500)

    total_amount = round(sum(e.get("amount", 0) for e in entries), 2)
    entries_count = len(entries)

    await db.settlement_runs.update_one(
        {"org_id": org_id, "run_id": run_id},
        {"$set": {"total_amount": total_amount, "entries_count": entries_count}},
    )

    return {"linked": linked_count, "total_entries": entries_count, "total_amount": total_amount}


async def remove_entry_from_draft(org_id: str, run_id: str, entry_id: str) -> dict:
    db = await get_db()
    run = await db.settlement_runs.find_one({"org_id": org_id, "run_id": run_id}, {"_id": 0})
    if not run:
        return {"error": "Settlement run not found", "status_code": 404}
    if run["status"] != "draft":
        return {"error": "Entries can only be removed from draft runs", "status_code": 400}

    result = await db.ledger_entries.update_one(
        {"org_id": org_id, "entry_id": entry_id, "settlement_run_id": run_id},
        {"$set": {"settlement_run_id": None}},
    )
    if result.modified_count == 0:
        return {"error": "Entry not found in this run", "status_code": 404}

    entries = await db.ledger_entries.find(
        {"org_id": org_id, "settlement_run_id": run_id}, {"_id": 0}
    ).to_list(length=500)

    total_amount = round(sum(e.get("amount", 0) for e in entries), 2)
    entries_count = len(entries)

    await db.settlement_runs.update_one(
        {"org_id": org_id, "run_id": run_id},
        {"$set": {"total_amount": total_amount, "entries_count": entries_count}},
    )

    return {"removed": entry_id, "total_entries": entries_count, "total_amount": total_amount}


async def get_unassigned_entries(
    org_id: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    db = await get_db()
    query: dict = {"org_id": org_id, "settlement_run_id": None, "financial_status": "posted"}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id

    cursor = db.ledger_entries.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
