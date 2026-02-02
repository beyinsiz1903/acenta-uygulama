from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request

from app.auth import get_current_user, require_roles
from app.config import API_PREFIX
from app.context.org_context import get_current_org
from app.db import get_db
from app.errors import AppError
from app.schemas_ops_incidents import (
    OpsIncidentDetailOut,
    OpsIncidentListResponse,
    OpsIncidentSeverity,
    OpsIncidentSourceRef,
    OpsIncidentStatus,
    OpsIncidentType,
)
from app.services.ops_incidents_service import resolve_incident


router = APIRouter(prefix=f"{API_PREFIX}/admin/ops/incidents", tags=["ops-incidents"])


SEVERITY_RANK: Dict[OpsIncidentSeverity, int] = {
    "critical": 3,
    "high": 2,
    "medium": 1,
    "low": 0,
}


def _enforce_pagination(limit: Optional[int], offset: Optional[int]) -> tuple[int, int]:
    l = limit or 50
    o = offset or 0
    if l > 200:
        l = 200
    if o > 10_000:
        o = 10_000
    if l < 1:
        l = 1
    if o < 0:
        o = 0
    return l, o


@router.get("", response_model=OpsIncidentListResponse)
async def list_incidents(
    request: Request,
    type: Optional[OpsIncidentType] = Query(None),
    status: Optional[OpsIncidentStatus] = Query(None),
    severity: Optional[OpsIncidentSeverity] = Query(None),
    limit: Optional[int] = Query(50, ge=1),
    offset: Optional[int] = Query(0, ge=0),
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    _roles=Depends(require_roles(["agency_admin", "super_admin"])),
) -> OpsIncidentListResponse:
    organization_id: str = org["id"]

    flt: Dict[str, Any] = {"organization_id": organization_id}
    if type is not None:
        flt["type"] = type
    if status is not None:
        flt["status"] = status
    if severity is not None:
        flt["severity"] = severity

    total = await db.ops_incidents.count_documents(flt)

    # Fetch a reasonable upper bound and sort in Python for deterministic ordering
    raw: List[Dict[str, Any]] = []
    cursor = db.ops_incidents.find(flt, {"_id": 0})
    async for doc in cursor:
        raw.append(doc)

    def _status_rank(s: str) -> int:
        return 1 if s == "open" else 0

    def _severity_rank(s: str) -> int:
        return SEVERITY_RANK.get(s, 0)

    raw.sort(
        key=lambda d: (
            _status_rank(d.get("status", "resolved")),
            _severity_rank(d.get("severity", "low")),
            d.get("created_at"),
        ),
        reverse=True,
    )

    l, o = _enforce_pagination(limit, offset)
    page = raw[o : o + l]

    items = []
    for d in page:
        src = d.get("source_ref") or {}
        src_model = OpsIncidentSourceRef(**src)
        items.append(
            {
                "incident_id": d.get("incident_id"),
                "type": d.get("type"),
                "severity": d.get("severity"),
                "status": d.get("status"),
                "summary": d.get("summary"),
                "created_at": d.get("created_at"),
                "source_ref": src_model,
            }
        )

    return OpsIncidentListResponse(total=total, items=items)


@router.get("/{incident_id}", response_model=OpsIncidentDetailOut)
async def get_incident_detail(
    incident_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    _roles=Depends(require_roles(["agency_admin", "super_admin"])),
) -> OpsIncidentDetailOut:
    organization_id: str = org["id"]
    doc = await db.ops_incidents.find_one(
        {"organization_id": organization_id, "incident_id": incident_id}, {"_id": 0}
    )
    if not doc:
        raise AppError(404, "INCIDENT_NOT_FOUND", "Incident not found")

    return OpsIncidentDetailOut(**doc)


@router.patch("/{incident_id}/resolve")
async def resolve_incident_endpoint(
    incident_id: str,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_org),
    _roles=Depends(require_roles(["agency_admin", "super_admin"])),
):
    organization_id: str = org["id"]

    # Resolve via service (includes validation and status checks)
    incident = await resolve_incident(
        db,
        organization_id=organization_id,
        incident_id=incident_id,
        current_user=user,
    )

    # Best-effort audit
    try:
        from app.services.audit import write_audit_log

        actor = {
            "actor_type": "user",
            "email": user.get("email"),
            "roles": user.get("roles") or [],
        }
        meta = {
            "type": incident.type,
            "severity": incident.severity,
            "source_ref": incident.source_ref.model_dump(),
        }
        db_obj = await get_db()
        await write_audit_log(
            db_obj,
            organization_id=organization_id,
            actor=actor,
            request=request,
            action="OPS_INCIDENT_RESOLVED",
            target_type="incident",
            target_id=incident.incident_id,
            before=None,
            after=None,
            meta=meta,
        )
    except Exception:
        pass

    return {"incident_id": incident.incident_id, "status": "resolved"}
