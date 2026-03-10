from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_feature, require_roles
from app.db import get_db
from app.repositories.base_repository import with_org_filter, with_tenant_filter
from app.services.audit import write_audit_log
from app.services.agency_module_service import normalize_agency_modules
from app.services.agency_contract_status_service import (
    build_agency_contract_summary,
    get_agency_active_user_counts,
)
from app.utils import now_utc, serialize_doc
from app.utils_ids import build_id_filter


router = APIRouter(prefix="/api/admin/agencies", tags=["admin_agencies"])

AdminDep = Depends(require_roles(["admin", "super_admin"]))
FeatureDep = Depends(require_feature("b2b_pro"))


class AgencyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    # For V1 we keep commission/discount optional; existing fields preserved when null on update.
    discount_percent: Optional[float] = None
    commission_percent: Optional[float] = None
    parent_agency_id: Optional[str] = None
    contract_start_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    contract_end_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    payment_status: Optional[str] = Field(default=None, pattern="^(paid|pending|overdue)$")
    package_type: Optional[str] = Field(default=None, max_length=120)
    user_limit: Optional[int] = Field(default=None, ge=1)


class AgencyCreate(AgencyBase):
    pass


class AgencyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    discount_percent: Optional[float] = None
    commission_percent: Optional[float] = None
    parent_agency_id: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(active|disabled)$")
    contract_start_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    contract_end_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    payment_status: Optional[str] = Field(default=None, pattern="^(paid|pending|overdue)$")
    package_type: Optional[str] = Field(default=None, max_length=120)
    user_limit: Optional[int] = Field(default=None, ge=1)


def _request_tenant_id(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    return getattr(request.state, "tenant_id", None)


async def _load_agency_by_id(db, org_id: str, agency_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    flt: Dict[str, Any] = with_org_filter({}, org_id)
    if tenant_id:
        flt = with_tenant_filter(flt, tenant_id, include_legacy_without_tenant=True)
    flt.update(build_id_filter(agency_id, field_name="_id"))
    return await db.agencies.find_one(flt)


async def _validate_parent_chain(
    db,
    *,
    org_id: str,
    current_agency_id: Optional[str],
    parent_agency_id: Optional[str],
    tenant_id: Optional[str] = None,
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

        flt: Dict[str, Any] = with_org_filter({}, org_id)
        if tenant_id:
            flt = with_tenant_filter(flt, tenant_id, include_legacy_without_tenant=True)
        flt.update(build_id_filter(cursor_id, field_name="_id"))
        doc = await db.agencies.find_one(flt)
        if not doc:
            # Parent not in this org; treat as invalid for V1
            raise HTTPException(status_code=404, detail="PARENT_AGENCY_NOT_FOUND")

        raw_parent = doc.get("parent_agency_id")
        if not raw_parent:
            break

        cursor_id = str(raw_parent)


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _parse_contract_date(value: Optional[str]) -> Optional[date]:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value)[:10])


def _validate_contract_window(*, start_date: Optional[str], end_date: Optional[str]) -> None:
    try:
        parsed_start = _parse_contract_date(start_date)
        parsed_end = _parse_contract_date(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"CONTRACT_DATE_INVALID: {exc}") from exc

    if parsed_start and parsed_end and parsed_end < parsed_start:
        raise HTTPException(status_code=422, detail="CONTRACT_DATE_RANGE_INVALID")


def _agency_audit_view(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": doc.get("name"),
        "discount_percent": doc.get("discount_percent"),
        "commission_percent": doc.get("commission_percent"),
        "parent_agency_id": doc.get("parent_agency_id"),
        "status": doc.get("status"),
        "contract_start_date": doc.get("contract_start_date"),
        "contract_end_date": doc.get("contract_end_date"),
        "payment_status": doc.get("payment_status"),
        "package_type": doc.get("package_type"),
        "user_limit": doc.get("user_limit"),
    }


def _serialize_agency_with_contract(doc: Dict[str, Any], *, active_user_count: int = 0) -> Dict[str, Any]:
    payload = serialize_doc(doc)
    summary = build_agency_contract_summary(doc, active_user_count=active_user_count)
    payload["contract_summary"] = summary
    payload["active_user_count"] = summary.get("active_user_count")
    payload["remaining_user_slots"] = summary.get("remaining_user_slots")
    return payload


@router.get("/", dependencies=[AdminDep, FeatureDep])
async def list_agencies(request: Request, user=Depends(get_current_user), db=Depends(get_db)) -> List[Dict[str, Any]]:
    org_id = user["organization_id"]
    tenant_id = _request_tenant_id(request)
    flt: Dict[str, Any] = with_org_filter({}, org_id)
    if tenant_id:
        flt = with_tenant_filter(flt, str(tenant_id), include_legacy_without_tenant=True)
    docs = await db.agencies.find(flt).sort("created_at", -1).to_list(500)
    user_counts = await get_agency_active_user_counts(
        db,
        organization_id=org_id,
        agency_ids=[doc.get("_id") for doc in docs],
        tenant_id=tenant_id,
    )
    return [
        _serialize_agency_with_contract(doc, active_user_count=user_counts.get(str(doc.get("_id")), 0))
        for doc in docs
    ]


@router.post("/", dependencies=[AdminDep, FeatureDep])
async def create_agency(payload: AgencyCreate, request: Request, user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user["organization_id"]
    tenant_id = _request_tenant_id(request)

    _validate_contract_window(
        start_date=payload.contract_start_date,
        end_date=payload.contract_end_date,
    )

    # Validate parent chain (creation: current_agency_id is None)
    await _validate_parent_chain(
        db,
        org_id=org_id,
        current_agency_id=None,
        parent_agency_id=payload.parent_agency_id,
        tenant_id=tenant_id,
    )

    now = now_utc()
    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "name": payload.name.strip(),
        "discount_percent": payload.discount_percent or 0.0,
        "commission_percent": payload.commission_percent or 0.0,
        "parent_agency_id": payload.parent_agency_id,
        "status": "active",
        "contract_start_date": payload.contract_start_date,
        "contract_end_date": payload.contract_end_date,
        "payment_status": payload.payment_status,
        "package_type": _normalize_optional_text(payload.package_type),
        "user_limit": payload.user_limit,
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
            after=_agency_audit_view(doc),
            meta={},
        )
    except Exception:
        # Audit failures must not break main flow
        pass

    return _serialize_agency_with_contract(created)


@router.put("/{agency_id}", dependencies=[AdminDep, FeatureDep])
async def update_agency(
    agency_id: str,
    payload: AgencyUpdate,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    org_id = user["organization_id"]
    tenant_id = _request_tenant_id(request)

    existing = await _load_agency_by_id(db, org_id, agency_id, tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AGENCY_NOT_FOUND")

    data = payload.model_dump(exclude_unset=True)

    next_start = data.get("contract_start_date") if "contract_start_date" in data else existing.get("contract_start_date")
    next_end = data.get("contract_end_date") if "contract_end_date" in data else existing.get("contract_end_date")
    _validate_contract_window(start_date=next_start, end_date=next_end)

    # Determine new parent (explicit None allowed to clear parent)
    new_parent = data.get("parent_agency_id") if "parent_agency_id" in data else existing.get("parent_agency_id")

    await _validate_parent_chain(
        db,
        org_id=org_id,
        current_agency_id=str(existing.get("_id")),
        parent_agency_id=new_parent,
        tenant_id=tenant_id,
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
    if "contract_start_date" in data:
        update_fields["contract_start_date"] = payload.contract_start_date
    if "contract_end_date" in data:
        update_fields["contract_end_date"] = payload.contract_end_date
    if "payment_status" in data:
        update_fields["payment_status"] = payload.payment_status
    if "package_type" in data:
        update_fields["package_type"] = _normalize_optional_text(payload.package_type)
    if "user_limit" in data:
        update_fields["user_limit"] = payload.user_limit

    if not update_fields:
        return serialize_doc(existing)

    update_fields["updated_at"] = now_utc()
    update_fields["updated_by"] = user.get("email")

    before = _agency_audit_view(existing)

    await db.agencies.update_one(
        with_tenant_filter({"_id": existing["_id"], "organization_id": org_id}, tenant_id, include_legacy_without_tenant=True) if tenant_id else {"_id": existing["_id"], "organization_id": org_id},
        {"$set": update_fields},
    )

    updated = await _load_agency_by_id(db, org_id, str(existing["_id"]), tenant_id)

    # Audit: AGENCY_UPDATED / AGENCY_DISABLED based on status change
    try:
        action = "AGENCY_UPDATED"
        if before.get("status") != "disabled" and update_fields.get("status") == "disabled":
            action = "AGENCY_DISABLED"

        after = _agency_audit_view(updated)

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

    return _serialize_agency_with_contract(updated)


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
    tenant_id = _request_tenant_id(request)
    existing = await _load_agency_by_id(db, org_id, agency_id, tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AGENCY_NOT_FOUND")

    before_status = existing.get("status") or "active"

    await db.agencies.update_one(
        with_tenant_filter({"_id": existing["_id"], "organization_id": org_id}, tenant_id, include_legacy_without_tenant=True) if tenant_id else {"_id": existing["_id"], "organization_id": org_id},
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

    updated = await _load_agency_by_id(db, org_id, str(existing["_id"]), tenant_id)
    return serialize_doc(updated)



# ══════════════════════════════════════════════════════════
# Per-Agency Module (Tab) Management
# ══════════════════════════════════════════════════════════

class AgencyModulesUpdate(BaseModel):
    allowed_modules: List[str] = Field(..., description="List of allowed modeKey values")


@router.get("/{agency_id}/modules", dependencies=[AdminDep])
async def get_agency_modules(
    agency_id: str,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Get allowed modules for a specific agency."""
    org_id = user["organization_id"]
    tenant_id = _request_tenant_id(request)
    existing = await _load_agency_by_id(db, org_id, agency_id, tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AGENCY_NOT_FOUND")
    return {
        "agency_id": str(existing["_id"]),
        "agency_name": existing.get("name", ""),
        "allowed_modules": normalize_agency_modules(existing.get("allowed_modules", [])),
    }


@router.put("/{agency_id}/modules", dependencies=[AdminDep])
async def update_agency_modules(
    agency_id: str,
    payload: AgencyModulesUpdate,
    request: Request,
    user=Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Update allowed modules for a specific agency."""
    org_id = user["organization_id"]
    tenant_id = _request_tenant_id(request)
    existing = await _load_agency_by_id(db, org_id, agency_id, tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AGENCY_NOT_FOUND")

    normalized_modules = normalize_agency_modules(payload.allowed_modules)

    await db.agencies.update_one(
        with_tenant_filter({"_id": existing["_id"], "organization_id": org_id}, tenant_id, include_legacy_without_tenant=True) if tenant_id else {"_id": existing["_id"], "organization_id": org_id},
        {"$set": {
            "allowed_modules": normalized_modules,
            "updated_at": now_utc(),
            "updated_by": user.get("email"),
        }},
    )

    return {
        "agency_id": str(existing["_id"]),
        "agency_name": existing.get("name", ""),
        "allowed_modules": normalized_modules,
    }
