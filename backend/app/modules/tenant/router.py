"""Tenant Isolation Admin API — monitoring and enforcement endpoints.

Provides:
- Health check for tenant isolation status
- Violation log viewer
- Index enforcement runner
- Collection audit
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth import get_current_user, is_super_admin
from app.db import get_db
from app.modules.tenant.admin_bypass import TENANT_SCOPED_COLLECTIONS
from app.modules.tenant.guard import run_tenant_isolation_health_check

router = APIRouter(
    prefix="/api/admin/tenant-isolation",
    tags=["Tenant Isolation Admin"],
)


@router.get("/health")
async def tenant_isolation_health(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Run tenant isolation health check (super admin only)."""
    if not is_super_admin(user):
        return {"error": "Super admin only"}
    report = await run_tenant_isolation_health_check(db)
    return {"status": "ok", "report": report}


@router.get("/violations")
async def list_violations(
    limit: int = 50,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List recent tenant isolation violations (super admin only)."""
    if not is_super_admin(user):
        return {"error": "Super admin only"}

    violations = await db.tenant_isolation_violations.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"violations": violations, "count": len(violations)}


@router.post("/ensure-indexes")
async def ensure_tenant_indexes(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create organization_id indexes on all tenant-scoped collections."""
    if not is_super_admin(user):
        return {"error": "Super admin only"}

    created = []
    skipped = []
    errors = []

    for coll_name in sorted(TENANT_SCOPED_COLLECTIONS):
        try:
            coll = db[coll_name]
            indexes = await coll.index_information()
            has_org_index = any(
                "organization_id" in str(idx.get("key", ""))
                for idx in indexes.values()
            )
            if has_org_index:
                skipped.append(coll_name)
                continue

            await coll.create_index(
                [("organization_id", 1)],
                name=f"idx_{coll_name}_org_id",
                background=True,
            )
            created.append(coll_name)
        except Exception as exc:
            errors.append({"collection": coll_name, "error": str(exc)})

    return {
        "status": "ok",
        "created_indexes": created,
        "already_indexed": skipped,
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/orphaned-documents")
async def find_orphaned_documents(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Find documents missing organization_id in tenant-scoped collections."""
    if not is_super_admin(user):
        return {"error": "Super admin only"}

    orphans = {}
    for coll_name in sorted(TENANT_SCOPED_COLLECTIONS):
        coll = db[coll_name]
        count = await coll.count_documents({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": None},
                {"organization_id": ""},
            ]
        })
        if count > 0:
            orphans[coll_name] = count

    return {
        "status": "ok",
        "orphaned_documents": orphans,
        "total_orphaned": sum(orphans.values()),
        "collections_affected": len(orphans),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/scope-summary")
async def scope_summary(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Summary of tenant scoping status across all collections."""
    if not is_super_admin(user):
        return {"error": "Super admin only"}

    summary = []
    for coll_name in sorted(TENANT_SCOPED_COLLECTIONS):
        coll = db[coll_name]
        total = await coll.estimated_document_count()
        if total == 0:
            summary.append({
                "collection": coll_name,
                "total": 0,
                "scoped": 0,
                "unscoped": 0,
                "coverage": 100.0,
            })
            continue

        unscoped = await coll.count_documents({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": None},
            ]
        })
        scoped = total - unscoped
        coverage = round((scoped / total) * 100, 1) if total > 0 else 100.0
        summary.append({
            "collection": coll_name,
            "total": total,
            "scoped": scoped,
            "unscoped": unscoped,
            "coverage": coverage,
        })

    return {
        "status": "ok",
        "collections": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
