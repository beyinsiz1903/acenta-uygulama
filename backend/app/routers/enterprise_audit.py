"""Enterprise Immutable Audit router (E1.3).

Hash-chained audit logs with CSV streaming export.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit_hash_chain import verify_chain_integrity, write_chained_audit_log
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/audit", tags=["enterprise_audit"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


@router.get("/chain", dependencies=[AdminDep])
async def list_audit_chain(
    tenant_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List hash-chained audit logs."""
    db = await get_db()
    org_id = user["organization_id"]
    query = {"organization_id": org_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    if action:
        query["action"] = action

    cursor = db.audit_logs_chain.find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"items": [serialize_doc(d) for d in docs], "count": len(docs)}


@router.get("/chain/verify", dependencies=[AdminDep])
async def verify_audit_chain(
    tenant_id: str = Query(...),
    user=Depends(get_current_user),
):
    """Verify hash chain integrity for a tenant."""
    db = await get_db()
    result = await verify_chain_integrity(db, tenant_id)
    return result


@router.get("/export", dependencies=[AdminDep])
async def export_audit_csv(
    tenant_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    user=Depends(get_current_user),
):
    """Export audit logs as streaming CSV."""
    db = await get_db()
    org_id = user["organization_id"]

    query = {"organization_id": org_id}
    if tenant_id:
        query["tenant_id"] = tenant_id

    date_filter = {}
    if from_date:
        try:
            date_filter["$gte"] = datetime.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'from' date format")
    if to_date:
        try:
            date_filter["$lte"] = datetime.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'to' date format")
    if date_filter:
        query["created_at"] = date_filter

    # Also search in legacy audit_logs
    # Streaming generator for memory safety
    async def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "tenant_id", "action", "target_type", "target_id",
            "actor_email", "actor_type", "created_at",
            "previous_hash", "current_hash",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Export from chained audit logs
        cursor = db.audit_logs_chain.find(query).sort("created_at", 1)
        async for doc in cursor:
            actor = doc.get("actor") or {}
            target = doc.get("target") or {}
            created = doc.get("created_at", "")
            if isinstance(created, datetime):
                created = created.isoformat()

            writer.writerow([
                doc.get("_id", ""),
                doc.get("tenant_id", ""),
                doc.get("action", ""),
                target.get("type", ""),
                target.get("id", ""),
                actor.get("email", ""),
                actor.get("actor_type", ""),
                created,
                doc.get("previous_hash", ""),
                doc.get("current_hash", ""),
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

        # Also export from legacy audit_logs
        legacy_query = {"organization_id": org_id}
        if tenant_id:
            legacy_query["tenant_id"] = tenant_id
        if date_filter:
            legacy_query["created_at"] = date_filter

        cursor2 = db.audit_logs.find(legacy_query).sort("created_at", 1)
        async for doc in cursor2:
            actor = doc.get("actor") or {}
            target = doc.get("target") or {}
            created = doc.get("created_at", "")
            if isinstance(created, datetime):
                created = created.isoformat()

            writer.writerow([
                doc.get("_id", ""),
                doc.get("tenant_id", ""),
                doc.get("action", ""),
                target.get("type", ""),
                target.get("id", ""),
                actor.get("email", ""),
                actor.get("actor_type", ""),
                created,
                "",  # No hash in legacy
                "",
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )
