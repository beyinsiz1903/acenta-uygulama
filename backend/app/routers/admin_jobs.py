from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_feature, require_roles
from app.db import get_db
from app.utils import serialize_doc


router = APIRouter(prefix="/api/admin/jobs", tags=["admin_jobs"])


AdminDep = Depends(require_roles(["super_admin"]))
FeatureDep = Depends(require_feature("job_platform"))


def _to_oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz id")


@router.get("/")
async def list_jobs(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None, alias="job_type"),
    limit: int = Query(50, ge=1, le=200),
    user: Dict[str, Any] = AdminDep,
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")

    q: Dict[str, Any] = {"organization_id": org_id}
    if status:
        q["status"] = status
    if type:
        q["type"] = type

    cursor = (
        db.jobs.find(q, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    return {"items": items}


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    user: Dict[str, Any] = AdminDep,
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")

    oid = _to_oid(job_id)
    doc = await db.jobs.find_one({"_id": oid, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return doc


async def _set_job_pending(db, org_id: str, job_id: str) -> Dict[str, Any]:
    oid = _to_oid(job_id)
    now = datetime.now(timezone.utc)
    doc = await db.jobs.find_one_and_update(
        {"_id": oid, "organization_id": org_id},
        {
            "$set": {
                "status": "pending",
                "next_run_at": now,
                "updated_at": now,
            }
        },
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    doc.pop("_id", None)
    return doc


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    user: Dict[str, Any] = AdminDep,
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")
    doc = await _set_job_pending(db, org_id, job_id)
    return {"ok": True, "job": doc}


@router.post("/{job_id}/dead-letter/revive")
async def revive_dead_job(
    job_id: str,
    user: Dict[str, Any] = AdminDep,
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id missing")

    oid = _to_oid(job_id)
    now = datetime.now(timezone.utc)
    doc = await db.jobs.find_one_and_update(
        {"_id": oid, "organization_id": org_id},
        {
            "$set": {
                "status": "pending",
                "next_run_at": now,
                "updated_at": now,
            }
        },
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")

    doc.pop("_id", None)
    return {"ok": True, "job": doc}
