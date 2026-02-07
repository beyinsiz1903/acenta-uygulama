"""O5 - Incident Tracking Admin Endpoints.

GET   /api/admin/system/incidents             - List incidents
POST  /api/admin/system/incidents             - Create incident
PATCH /api/admin/system/incidents/{id}/resolve - Resolve incident
"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_roles
from app.db import get_db
from app.services import incident_service
from app.services.audit_hash_chain import write_chained_audit_log

router = APIRouter(
    prefix="/api/admin/system/incidents",
    tags=["system_incidents"],
)


class IncidentCreate(BaseModel):
    severity: str = "medium"
    title: str
    affected_tenants: List[str] = []
    root_cause: str = ""
    resolution_notes: Optional[str] = None


class IncidentResolve(BaseModel):
    resolution_notes: str


@router.get("")
async def list_incidents(
    skip: int = 0,
    limit: int = 50,
    severity: Optional[str] = None,
    user=Depends(require_roles(["super_admin"])),
):
    """List system incidents."""
    items = await incident_service.list_incidents(skip=skip, limit=limit, severity=severity)
    return {"items": items, "total": len(items)}


@router.post("")
async def create_incident(
    body: IncidentCreate,
    user=Depends(require_roles(["super_admin"])),
):
    """Create a new system incident."""
    result = await incident_service.create_incident(
        severity=body.severity,
        title=body.title,
        affected_tenants=body.affected_tenants,
        root_cause=body.root_cause,
        resolution_notes=body.resolution_notes,
    )

    # Audit log
    db = await get_db()
    await write_chained_audit_log(
        db,
        organization_id=user.get("organization_id", ""),
        tenant_id=user.get("tenant_id", ""),
        actor={"actor_type": "user", "actor_id": str(user.get("_id", "")), "email": user.get("email", "")},
        action="system.incident.create",
        target_type="system_incident",
        target_id=result.get("incident_id", ""),
        after={"severity": body.severity, "title": body.title},
    )

    return result


@router.patch("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    body: IncidentResolve,
    user=Depends(require_roles(["super_admin"])),
):
    """Resolve a system incident."""
    result = await incident_service.resolve_incident(
        incident_id=incident_id,
        resolution_notes=body.resolution_notes,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Audit log
    db = await get_db()
    await write_chained_audit_log(
        db,
        organization_id=user.get("organization_id", ""),
        tenant_id=user.get("tenant_id", ""),
        actor={"actor_type": "user", "actor_id": str(user.get("_id", "")), "email": user.get("email", "")},
        action="system.incident.resolve",
        target_type="system_incident",
        target_id=incident_id,
        after={"resolution_notes": body.resolution_notes},
    )

    return result
