"""Approval Workflow Engine (E1.2).

Creates approval requests for actions that exceed thresholds.
Supports: refunds, high-value payments (>50k).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.utils import now_utc, serialize_doc

PAYMENT_APPROVAL_THRESHOLD = 50000  # Amount threshold for payment approval


async def create_approval_request(
    *,
    tenant_id: str,
    organization_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    payload: Dict[str, Any],
    requested_by: str,
) -> Dict[str, Any]:
    """Create a new approval request."""
    db = await get_db()
    now = now_utc()

    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "payload": payload,
        "status": "pending",
        "requested_by": requested_by,
        "approved_by": None,
        "rejected_by": None,
        "resolution_note": None,
        "created_at": now,
        "resolved_at": None,
    }

    await db.approval_requests.insert_one(doc)
    return serialize_doc(doc)


async def list_approvals(
    tenant_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List approval requests."""
    db = await get_db()
    query: Dict[str, Any] = {}
    if tenant_id:
        query["tenant_id"] = tenant_id
    if organization_id:
        query["organization_id"] = organization_id
    if status:
        query["status"] = status

    cursor = db.approval_requests.find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [serialize_doc(d) for d in docs]


async def get_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    """Get a single approval request."""
    db = await get_db()
    doc = await db.approval_requests.find_one({"_id": approval_id})
    return serialize_doc(doc) if doc else None


async def approve_request(
    approval_id: str,
    approved_by: str,
    note: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Approve a pending request. Returns None if not found/already resolved."""
    db = await get_db()
    now = now_utc()

    result = await db.approval_requests.find_one_and_update(
        {"_id": approval_id, "status": "pending"},
        {
            "$set": {
                "status": "approved",
                "approved_by": approved_by,
                "resolution_note": note,
                "resolved_at": now,
            }
        },
        return_document=True,
    )
    if not result:
        return None
    return serialize_doc(result)


async def reject_request(
    approval_id: str,
    rejected_by: str,
    note: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Reject a pending request. Returns None if not found/already resolved."""
    db = await get_db()
    now = now_utc()

    result = await db.approval_requests.find_one_and_update(
        {"_id": approval_id, "status": "pending"},
        {
            "$set": {
                "status": "rejected",
                "rejected_by": rejected_by,
                "resolution_note": note,
                "resolved_at": now,
            }
        },
        return_document=True,
    )
    if not result:
        return None
    return serialize_doc(result)


def needs_approval_for_payment(amount: float) -> bool:
    """Check if payment amount exceeds approval threshold."""
    return amount > PAYMENT_APPROVAL_THRESHOLD
