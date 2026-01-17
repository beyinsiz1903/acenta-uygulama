from __future__ import annotations

from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_feature, require_roles
from app.db import get_db
from app.services.audit import write_audit_log
from app.utils import now_utc, serialize_doc
from app.utils.ids import build_id_filter


router = APIRouter(prefix="/api/admin/agencies", tags=["admin_agencies"])

AdminDep = Depends(require_roles(["admin", "super_admin"]))
FeatureDep = Depends(require_feature("b2b_pro"))


class AgencyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    # For V1 we keep commission/discount optional; existing fields preserved when null on update.
    discount_percent: Optional[float] = None
    commission_percent: Optional[float] = None
    parent_agency_id: Optional[str] = None


class AgencyCreate(AgencyBase):
    pass


class AgencyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    discount_percent: Optional[float] = None
    commission_percent: Optional[float] = None
    parent_agency_id: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(active|disabled)$")


async def _load_agency_by_id(db, org_id: str, agency_id: str) -> Optional[Dict[str, Any]]:
    flt: Dict[str, Any] = {"organization_id": org_id}
    flt.update(build_id_filter(agency_id, field_name="_id"))
    return await db.agencies.find_one(flt)


async def _validate_parent_chain(
    db,
    *,
    org_id: str,
    current_agency_id: Optional[str],
    parent_agency_id: Optional[str],
) -> None:
    """Detect self-parent and simple cycles in parent chain.

    - self-parent: parent_agency_id == current_agency_id -> 422
    - cycle: walking up the chain hits any seen ID again -> 422
    """

    if not parent_agency_id:
        return

    parent_id_str = str(parent_agency_id)
    current_id_str = str(current_agency_id) if current_agency_id else None

    # Self-parent guard
    if current_id_str and parent_id_str == current_id_str:
        raise HTTPException(status_code=422, detail="SELF_PARENT_NOT_ALLOWED")

    seen = set()
    if current_id_str:
        seen.add(current_id_str)

    cursor_id: Optional[str] = parent_id_str

    while cursor_id:
        if cursor_id in seen:
            # Cycle detected
            raise HTTPException(status_code=422, detail="PARENT_CYCLE_DETECTED")

        seen.add(cursor_id)

        flt: Dict[str, Any] = {"organization_id": org_id}
        flt.update(build_id_filter(cursor_id, field_name="_id"))
        doc = await db.agencies.find_one(flt)
        if not doc:
            # Parent not in this org; treat as invalid for V1
            raise HTTPException(status_code=404, detail="PARENT_AGENCY_NOT_FOUND")

        raw_parent = doc.get("parent_agency_id")
        if not raw_parent:
            break

        cursor_id = str(raw_parent)


@router.get("/", dependencies=[AdminDep, FeatureDep])
async def list_agencies(user=Depends(get_current_user), db=Depends(get_db)) -> List[Dict[str, Any]]:
    org_id = user["organization_id"]
    docs = await db.agencies.find({"organization_id": org_id}).sort("created_at", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.post("/", dependencies=[AdminDep, FeatureDep])
async def create_agency(payload: AgencyCreate, request: Request, user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user["organization_id"]

    # Validate parent chain (creation: current_agency_id is None)
    await _validate_parent_chain(
        db,
        org_id=org_id,
        current_agency_id=None,
        parent_agency_id=payload.parent_agency_id,
    )

    now = now_utc()
    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "name": payload.name.strip(),
        "discount_percent": payload.discount_percent or 0.0,
        "commission_percent": payload.commission_percent or 0.0,
        "parent_agency_id": payload.parent_agency_id,
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
    }

    res = await db.agencies.insert_one(doc)
    created = await db.agencies.find_one({"_id": res.inserted_id})

    # Audit: AGENCY_CREATED (meta kept primitive)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
            request=request,
            action="AGENCY_CREATED",
            target_type="agency",
            target_id=str(res.inserted_id),
            before=None,
            after={
                "name": doc["name"],
                "discount_percent": doc["discount_percent"],
                "commission_percent": doc["commission_percent"],
                "parent_agency_id": doc["parent_agency_id"],
                "status": doc["status"],
            },
            meta={},
        )
    except Exception:
        # Audit failures must not break main flow
        pass

    return serialize_doc(created)


@router.put("/{agency_id}", dependencies=[AdminDep, FeatureDep])
async def update_agency(
    agency_id: str,
    payload: AgencyUpdate,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user["organization_id"]

    existing = await _load_agency_by_id(db, org_id, agency_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AGENCY_NOT_FOUND")

    # Determine new parent (explicit None allowed to clear parent)
    data = payload.model_dump(exclude_unset=True)
    new_parent = data.get("parent_agency_id") if "parent_agency_id" in data else existing.get("parent_agency_id")

    await _validate_parent_chain(
        db,
        org_id=org_id,
        current_agency_id=str(existing.get("_id")),
        parent_agency_id=new_parent,
    )

    update_fields: Dict[str, Any] = {}
    if payload.name is not None:
        update_fields["name"] = payload.name.strip()
    if payload.discount_percent is not None:
        update_fields["discount_percent"] = payload.discount_percent
    if payload.commission_percent is not None:
        update_fields["commission_percent"] = payload.commission_percent
    if "parent_agency_id" in data:
        update_fields["parent_agency_id"] = new_parent
    if payload.status is not None:
        update_fields["status"] = payload.status

    if not update_fields:
        return serialize_doc(existing)

    update_fields["updated_at"] = now_utc()
    update_fields["updated_by"] = user.get("email")

    before = {k: existing.get(k) for k in ["name", "discount_percent", "commission_percent", "parent_agency_id", "status"]}

    await db.agencies.update_one(
        {"_id": existing["_id"], "organization_id": org_id},
        {"$set": update_fields},
    )

    updated = await _load_agency_by_id(db, org_id, str(existing["_id"]))

    # Audit: AGENCY_UPDATED / AGENCY_DISABLED based on status change
    try:
        action = "AGENCY_UPDATED"
        if before.get("status") != "disabled" and update_fields.get("status") == "disabled":
            action = "AGENCY_DISABLED"

        after = {k: updated.get(k) for k in ["name", "discount_percent", "commission_percent", "parent_agency_id", "status"]}

        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
            request=request,
            action=action,
            target_type="agency",
            target_id=str(existing["_id"]),
            before=before,
            after=after,
            meta={},
        )
    except Exception:
        pass

    return serialize_doc(updated)


@router.delete("/{agency_id}", dependencies=[AdminDep, FeatureDep])
async def soft_delete_agency(
    agency_id: str,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Soft-delete agency by setting status to disabled.

    We keep document for referential integrity; no hard deletes.
    """

    org_id = user["organization_id"]
    existing = await _load_agency_by_id(db, org_id, agency_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AGENCY_NOT_FOUND")

    before_status = existing.get("status") or "active"

    await db.agencies.update_one(
        {"_id": existing["_id"], "organization_id": org_id},
        {"$set": {"status": "disabled", "updated_at": now_utc(), "updated_by": user.get("email")}},
    )

    # Audit: AGENCY_DISABLED
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles")},
            request=request,
            action="AGENCY_DISABLED",
            target_type="agency",
            target_id=str(existing["_id"]),
            before={"status": before_status},
            after={"status": "disabled"},
            meta={},
        )
    except Exception:
        pass

    updated = await _load_agency_by_id(db, org_id, str(existing["_id"]))
    return serialize_doc(updated)
