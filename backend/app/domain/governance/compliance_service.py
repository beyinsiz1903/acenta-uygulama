"""Enterprise Governance — Compliance Logging Service (Part 6).

Financial operation logging for tax audits and payment disputes.
Immutable compliance records with tamper-detection hashing.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("governance.compliance")


async def log_financial_operation(
    db: Any,
    org_id: str,
    *,
    operation_type: str,
    amount: float,
    currency: str,
    booking_id: str = "",
    payment_id: str = "",
    invoice_id: str = "",
    actor_email: str,
    counterparty: str = "",
    tax_details: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Log a financial operation for compliance purposes."""
    now = datetime.now(timezone.utc)
    doc_id = str(uuid.uuid4())

    # Get previous hash for chain integrity
    last_entry = await db.gov_compliance_log.find_one(
        {"organization_id": org_id},
        sort=[("sequence", -1)],
    )
    prev_hash = last_entry.get("entry_hash", "GENESIS") if last_entry else "GENESIS"
    sequence = (last_entry.get("sequence", 0) + 1) if last_entry else 1

    # Compute entry hash (chain-linked)
    hash_input = f"{prev_hash}|{org_id}|{operation_type}|{amount}|{currency}|{now.isoformat()}|{sequence}"
    entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    doc = {
        "_id": doc_id,
        "organization_id": org_id,
        "sequence": sequence,
        "operation_type": operation_type,
        "amount": amount,
        "currency": currency,
        "booking_id": booking_id,
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "actor_email": actor_email,
        "counterparty": counterparty,
        "tax_details": tax_details or {},
        "metadata": metadata or {},
        "timestamp": now,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
        "is_immutable": True,
    }
    await db.gov_compliance_log.insert_one(doc)

    return {
        "compliance_id": doc_id,
        "sequence": sequence,
        "operation_type": operation_type,
        "entry_hash": entry_hash,
        "timestamp": now.isoformat(),
    }


async def search_compliance_logs(
    db: Any,
    org_id: str,
    *,
    operation_type: Optional[str] = None,
    booking_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    currency: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> dict:
    """Search compliance logs with filters."""
    query: dict[str, Any] = {"organization_id": org_id}
    if operation_type:
        query["operation_type"] = operation_type
    if booking_id:
        query["booking_id"] = booking_id
    if currency:
        query["currency"] = currency
    if from_date or to_date:
        ts_filter: dict[str, Any] = {}
        if from_date:
            ts_filter["$gte"] = from_date
        if to_date:
            ts_filter["$lte"] = to_date
        query["timestamp"] = ts_filter
    if min_amount is not None or max_amount is not None:
        amount_filter: dict[str, Any] = {}
        if min_amount is not None:
            amount_filter["$gte"] = min_amount
        if max_amount is not None:
            amount_filter["$lte"] = max_amount
        query["amount"] = amount_filter

    total = await db.gov_compliance_log.count_documents(query)
    docs = await db.gov_compliance_log.find(
        query, {"_id": 0}
    ).sort("sequence", -1).skip(skip).limit(limit).to_list(limit)

    return {"total": total, "items": docs, "limit": limit, "skip": skip}


async def verify_compliance_chain(db: Any, org_id: str, last_n: int = 100) -> dict:
    """Verify integrity of the compliance log chain."""
    docs = await db.gov_compliance_log.find(
        {"organization_id": org_id}
    ).sort("sequence", 1).limit(last_n).to_list(last_n)

    if not docs:
        return {"verified": True, "entries_checked": 0, "status": "empty"}

    broken_links = []
    for i, doc in enumerate(docs):
        if i == 0:
            continue
        expected_prev_hash = docs[i - 1].get("entry_hash", "")
        actual_prev_hash = doc.get("prev_hash", "")
        if expected_prev_hash != actual_prev_hash:
            broken_links.append({
                "sequence": doc.get("sequence"),
                "expected_prev_hash": expected_prev_hash,
                "actual_prev_hash": actual_prev_hash,
            })

    return {
        "verified": len(broken_links) == 0,
        "entries_checked": len(docs),
        "broken_links": broken_links,
        "status": "intact" if not broken_links else "tampered",
    }


async def get_compliance_summary(db: Any, org_id: str, days: int = 90) -> dict:
    """Get compliance summary for reporting."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=days)

    pipeline = [
        {"$match": {"organization_id": org_id, "timestamp": {"$gte": from_date}}},
        {"$group": {
            "_id": {"type": "$operation_type", "currency": "$currency"},
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$amount"},
            "avg_amount": {"$avg": "$amount"},
        }},
    ]
    results = await db.gov_compliance_log.aggregate(pipeline).to_list(100)

    by_type = {}
    for r in results:
        key = f"{r['_id']['type']}_{r['_id']['currency']}"
        by_type[key] = {
            "operation_type": r["_id"]["type"],
            "currency": r["_id"]["currency"],
            "count": r["count"],
            "total_amount": round(r["total_amount"], 2),
            "avg_amount": round(r["avg_amount"], 2),
        }

    total_entries = await db.gov_compliance_log.count_documents(
        {"organization_id": org_id, "timestamp": {"$gte": from_date}}
    )

    return {
        "period_days": days,
        "total_entries": total_entries,
        "by_operation_type": by_type,
        "chain_integrity": (await verify_compliance_chain(db, org_id, 50))["status"],
    }
