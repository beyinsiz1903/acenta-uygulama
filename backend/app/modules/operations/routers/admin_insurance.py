from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/insurance", tags=["admin-insurance"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))

INSURANCE_TYPES = ["travel", "health", "cancellation", "baggage", "comprehensive"]
PROVIDERS = ["Mapfre", "Allianz", "Axa", "Eureko", "Groupama", "HDI"]


class InsurancePolicyCreate(BaseModel):
    policy_type: str = "travel"
    provider: str = ""
    customer_id: str = ""
    customer_name: str = ""
    booking_id: Optional[str] = None
    policy_number: str = ""
    start_date: str = ""
    end_date: str = ""
    destination: str = ""
    coverage_amount: float = 0.0
    premium: float = 0.0
    currency: str = "EUR"
    insured_persons: List[Dict[str, Any]] = []
    coverage_details: List[str] = []
    status: str = "active"
    notes: str = ""


class InsurancePolicyPatch(BaseModel):
    policy_type: Optional[str] = None
    provider: Optional[str] = None
    customer_name: Optional[str] = None
    policy_number: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    destination: Optional[str] = None
    coverage_amount: Optional[float] = None
    premium: Optional[float] = None
    currency: Optional[str] = None
    insured_persons: Optional[List[Dict[str, Any]]] = None
    coverage_details: Optional[List[str]] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "policy_type": doc.get("policy_type", "travel"),
        "provider": doc.get("provider", ""),
        "customer_id": doc.get("customer_id", ""),
        "customer_name": doc.get("customer_name", ""),
        "booking_id": doc.get("booking_id"),
        "policy_number": doc.get("policy_number", ""),
        "start_date": doc.get("start_date", ""),
        "end_date": doc.get("end_date", ""),
        "destination": doc.get("destination", ""),
        "coverage_amount": float(doc.get("coverage_amount", 0)),
        "premium": float(doc.get("premium", 0)),
        "currency": doc.get("currency", "EUR"),
        "insured_persons": doc.get("insured_persons", []),
        "coverage_details": doc.get("coverage_details", []),
        "status": doc.get("status", "active"),
        "notes": doc.get("notes", ""),
        "organization_id": doc.get("organization_id"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


async def _audit(db, org_id: str, user: dict, action: str, target_id: str, meta: dict = None):
    try:
        from app.services.audit import write_audit_log
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "email": user.get("email"), "roles": user.get("roles") or []},
            request=None,
            action=action,
            target_type="insurance_policy",
            target_id=target_id,
            before=None,
            after=None,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Audit log failed for %s: %s", action, target_id)


@router.get("", dependencies=[AdminDep])
async def list_policies(
    status: Optional[str] = None,
    provider: Optional[str] = None,
    policy_type: Optional[str] = None,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if status:
        filt["status"] = status
    if provider:
        filt["provider"] = provider
    if policy_type:
        filt["policy_type"] = policy_type
    if customer_id:
        filt["customer_id"] = customer_id
    if search:
        filt["customer_name"] = {"$regex": search, "$options": "i"}
    total = await db.insurance_policies.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = db.insurance_policies.find(filt, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    return {"items": [_doc_to_dict(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/types", dependencies=[AdminDep])
async def get_insurance_types():
    return {"types": INSURANCE_TYPES}


@router.get("/providers", dependencies=[AdminDep])
async def get_insurance_providers():
    return {"providers": PROVIDERS}


@router.get("/{policy_id}", dependencies=[AdminDep])
async def get_policy(policy_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.insurance_policies.find_one({"id": policy_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Police bulunamadi")
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_policy(body: InsurancePolicyCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    if not body.customer_id.strip():
        raise AppError(400, "INVALID", "Musteri secimi gereklidir")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
    }
    await db.insurance_policies.insert_one(doc)
    result = _doc_to_dict(doc)
    await _audit(db, org_id, user, "INSURANCE_CREATED", result["id"], {"provider": body.provider, "customer_name": body.customer_name})
    return result


@router.patch("/{policy_id}", dependencies=[AdminDep])
async def patch_policy(policy_id: str, body: InsurancePolicyPatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise AppError(400, "NO_CHANGES", "Guncelleme verisi yok")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.insurance_policies.update_one({"id": policy_id, "organization_id": org_id}, {"$set": updates})
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Police bulunamadi")
    doc = await db.insurance_policies.find_one({"id": policy_id, "organization_id": org_id}, {"_id": 0})
    await _audit(db, org_id, user, "INSURANCE_UPDATED", policy_id, {"fields": list(updates.keys())})
    return _doc_to_dict(doc)


@router.delete("/{policy_id}", dependencies=[AdminDep])
async def delete_policy(policy_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.insurance_policies.delete_one({"id": policy_id, "organization_id": org_id})
    if result.deleted_count == 0:
        raise AppError(404, "NOT_FOUND", "Police bulunamadi")
    await _audit(db, org_id, user, "INSURANCE_DELETED", policy_id)
    return {"ok": True}


@router.post("/{policy_id}/cancel", dependencies=[AdminDep])
async def cancel_policy(policy_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.insurance_policies.find_one({"id": policy_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Police bulunamadi")
    if doc.get("status") == "cancelled":
        raise AppError(400, "ALREADY_CANCELLED", "Bu police zaten iptal edilmis")

    now = datetime.now(timezone.utc).isoformat()
    await db.insurance_policies.update_one(
        {"id": policy_id, "organization_id": org_id},
        {"$set": {"status": "cancelled", "cancel_reason": payload.get("reason", ""), "updated_at": now}},
    )
    await _audit(db, org_id, user, "INSURANCE_CANCELLED", policy_id, {"reason": payload.get("reason", "")})
    return {"ok": True}


@router.post("/{policy_id}/renew", dependencies=[AdminDep])
async def renew_policy(policy_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.insurance_policies.find_one({"id": policy_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Police bulunamadi")

    now = datetime.now(timezone.utc).isoformat()
    new_doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "policy_type": doc.get("policy_type"),
        "provider": doc.get("provider"),
        "customer_id": doc.get("customer_id"),
        "customer_name": doc.get("customer_name"),
        "booking_id": payload.get("booking_id") or doc.get("booking_id"),
        "policy_number": payload.get("policy_number", ""),
        "start_date": payload.get("start_date", ""),
        "end_date": payload.get("end_date", ""),
        "destination": doc.get("destination"),
        "coverage_amount": payload.get("coverage_amount", doc.get("coverage_amount", 0)),
        "premium": payload.get("premium", doc.get("premium", 0)),
        "currency": doc.get("currency", "EUR"),
        "insured_persons": doc.get("insured_persons", []),
        "coverage_details": doc.get("coverage_details", []),
        "status": "active",
        "notes": f"Yenileme - Onceki police: {doc.get('policy_number', policy_id)}",
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
        "renewed_from": policy_id,
    }
    await db.insurance_policies.insert_one(new_doc)
    await _audit(db, org_id, user, "INSURANCE_RENEWED", new_doc["id"], {"renewed_from": policy_id})
    new_doc.pop("_id", None)
    return _doc_to_dict(new_doc)
