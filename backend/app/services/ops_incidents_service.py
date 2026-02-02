from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from app.schemas_ops_incidents import (
    OpsIncidentDetailOut,
    OpsIncidentSeverity,
    OpsIncidentStatus,
    OpsIncidentType,
    OpsIncidentSourceRef,
)
from app.utils import now_utc

SEVERITY_BY_TYPE: Dict[OpsIncidentType, OpsIncidentSeverity] = {
    "risk_review": "high",
    "supplier_partial_failure": "medium",
    "supplier_all_failed": "critical",
}


async def _find_open_incident(db, organization_id: str, inc_type: OpsIncidentType, dedup_filter: Dict[str, Any]) -> Optional[dict]:
    flt = {"organization_id": organization_id, "type": inc_type, "status": "open"}
    flt.update(dedup_filter)
    return await db.ops_incidents.find_one(flt)


async def create_incident(
    db,
    *,
    organization_id: str,
    inc_type: OpsIncidentType,
    source_ref: Dict[str, Any],
    summary: str,
    meta: Dict[str, Any],
    dedup_filter: Dict[str, Any],
) -> Optional[str]:
    """Create an ops incident with simple dedup on (org, type, dedup_filter, status=open).

    Returns incident_id or None if dedup prevented creation.
    """

    try:
        existing = await _find_open_incident(db, organization_id, inc_type, dedup_filter)
        if existing:
            return None

        now = now_utc()
        incident_id = f"inc_{uuid4().hex}"
        severity = SEVERITY_BY_TYPE.get(inc_type, "low")

        doc = {
            "incident_id": incident_id,
            "organization_id": organization_id,
            "type": inc_type,
            "severity": severity,
            "status": "open",
            "source_ref": source_ref,
            "summary": summary,
            "meta": meta or {},
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "resolved_by_user_id": None,
        }

        await db.ops_incidents.insert_one(doc)
        return incident_id
    except Exception:
        # Fail-open: never break main flows
        return None


async def resolve_incident(
    db,
    *,
    organization_id: str,
    incident_id: str,
    current_user: dict,
) -> OpsIncidentDetailOut:
    from app.errors import AppError

    doc = await db.ops_incidents.find_one(
        {"organization_id": organization_id, "incident_id": incident_id}
    )
    if not doc:
        raise AppError(404, "INCIDENT_NOT_FOUND", "Incident not found")

    if doc.get("status") != "open":
        raise AppError(400, "INCIDENT_ALREADY_RESOLVED", "Incident already resolved")

    now = now_utc()
    await db.ops_incidents.update_one(
        {"organization_id": organization_id, "incident_id": incident_id},
        {
            "$set": {
                "status": "resolved",
                "resolved_at": now,
                "resolved_by_user_id": str(current_user.get("id") or ""),
                "updated_at": now,
            }
        },
    )

    updated = await db.ops_incidents.find_one(
        {"organization_id": organization_id, "incident_id": incident_id}, {"_id": 0}
    )
    # Defensive default shape
    if not updated:
        raise AppError(404, "INCIDENT_NOT_FOUND", "Incident not found")

    # Pydantic will coerce nested dicts into OpsIncidentSourceRef automatically
    return OpsIncidentDetailOut(**updated)


async def create_risk_review_incident(
    db,
    *,
    organization_id: str,
    booking_id: str,
    risk_score: float,
    tenant_id: Optional[str],
    amount: float,
    currency: str,
) -> Optional[str]:
    meta = {
        "risk_score": risk_score,
        "tenant_id": tenant_id,
        "amount": amount,
        "currency": currency,
    }
    source_ref = {"booking_id": booking_id, "risk_decision": "REVIEW"}
    dedup = {"source_ref.booking_id": booking_id}
    return await create_incident(
        db,
        organization_id=organization_id,
        inc_type="risk_review",
        source_ref=source_ref,
        summary="Booking requires manual risk review.",
        meta=meta,
        dedup_filter=dedup,
    )


async def create_supplier_partial_failure_incident(
    db,
    *,
    organization_id: str,
    session_id: str,
    failed_suppliers: list[dict],
    succeeded_suppliers: list[str],
    warnings_count: int,
    offers_count: int,
) -> Optional[str]:
    meta = {
        "failed_suppliers": failed_suppliers,
        "succeeded_suppliers": succeeded_suppliers,
        "warnings_count": warnings_count,
        "offers_count": offers_count,
    }
    source_ref = {"session_id": session_id}
    dedup = {"source_ref.session_id": session_id}
    return await create_incident(
        db,
        organization_id=organization_id,
        inc_type="supplier_partial_failure",
        source_ref=source_ref,
        summary="Supplier partial failure during offers search.",
        meta=meta,
        dedup_filter=dedup,
    )


async def create_supplier_all_failed_incident(
    db,
    *,
    organization_id: str,
    session_id: str,
    requested_suppliers: list[str],
    failed_suppliers: list[str],
    warnings_count: int,
    request_fingerprint: str,
) -> Optional[str]:
    meta = {
        "requested_suppliers": requested_suppliers,
        "failed_suppliers": failed_suppliers,
        "warnings_count": warnings_count,
        "request_fingerprint": request_fingerprint,
        "session_id": session_id,
    }
    source_ref = {"session_id": session_id}
    dedup = {"meta.request_fingerprint": request_fingerprint}
    return await create_incident(
        db,
        organization_id=organization_id,
        inc_type="supplier_all_failed",
        source_ref=source_ref,
        summary="All suppliers failed during offers search.",
        meta=meta,
        dedup_filter=dedup,
    )
