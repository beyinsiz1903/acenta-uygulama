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

router = APIRouter(prefix="/api/admin/visa", tags=["admin-visa"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))

VISA_STATUSES = [
    "draft",
    "documents_collecting",
    "documents_ready",
    "submitted",
    "appointment_scheduled",
    "at_consulate",
    "approved",
    "rejected",
    "cancelled",
]

REQUIRED_DOCS = [
    "pasaport_kopya",
    "biyometrik_foto",
    "otel_rezervasyon",
    "ucak_bileti",
    "banka_hesap_ozeti",
    "sigorta_policesi",
    "is_belgesi",
    "davetiye_mektubu",
]


class VisaApplicationCreate(BaseModel):
    customer_id: str
    customer_name: str = ""
    destination_country: str = ""
    visa_type: str = "tourist"
    application_date: str = ""
    appointment_date: str = ""
    consulate: str = ""
    passport_number: str = ""
    passport_expiry: str = ""
    documents: List[Dict[str, Any]] = []
    notes: str = ""
    status: str = "draft"
    fee: float = 0.0
    currency: str = "EUR"
    booking_id: Optional[str] = None


class VisaApplicationPatch(BaseModel):
    customer_name: Optional[str] = None
    destination_country: Optional[str] = None
    visa_type: Optional[str] = None
    application_date: Optional[str] = None
    appointment_date: Optional[str] = None
    consulate: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[str] = None
    documents: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    fee: Optional[float] = None
    currency: Optional[str] = None


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "customer_id": doc.get("customer_id", ""),
        "customer_name": doc.get("customer_name", ""),
        "destination_country": doc.get("destination_country", ""),
        "visa_type": doc.get("visa_type", "tourist"),
        "application_date": doc.get("application_date", ""),
        "appointment_date": doc.get("appointment_date", ""),
        "consulate": doc.get("consulate", ""),
        "passport_number": doc.get("passport_number", ""),
        "passport_expiry": doc.get("passport_expiry", ""),
        "documents": doc.get("documents", []),
        "notes": doc.get("notes", ""),
        "status": doc.get("status", "draft"),
        "fee": float(doc.get("fee", 0)),
        "currency": doc.get("currency", "EUR"),
        "booking_id": doc.get("booking_id"),
        "timeline": doc.get("timeline", []),
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
            target_type="visa_application",
            target_id=target_id,
            before=None,
            after=None,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Audit log failed for %s: %s", action, target_id)


@router.get("", dependencies=[AdminDep])
async def list_visa_applications(
    status: Optional[str] = None,
    country: Optional[str] = None,
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
    if country:
        filt["destination_country"] = {"$regex": country, "$options": "i"}
    if customer_id:
        filt["customer_id"] = customer_id
    if search:
        filt["customer_name"] = {"$regex": search, "$options": "i"}
    total = await db.visa_applications.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = db.visa_applications.find(filt, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    return {"items": [_doc_to_dict(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/statuses", dependencies=[AdminDep])
async def get_visa_statuses():
    return {"statuses": VISA_STATUSES}


@router.get("/required-documents", dependencies=[AdminDep])
async def get_required_documents():
    return {"documents": REQUIRED_DOCS}


@router.get("/{visa_id}", dependencies=[AdminDep])
async def get_visa_application(visa_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.visa_applications.find_one({"id": visa_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        raise AppError(404, "NOT_FOUND", "Vize basvurusu bulunamadi")
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_visa_application(body: VisaApplicationCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    if not body.customer_id.strip():
        raise AppError(400, "INVALID", "Musteri secimi gereklidir")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "timeline": [{"date": now, "action": "created", "note": "Basvuru olusturuldu"}],
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
    }
    await db.visa_applications.insert_one(doc)
    result = _doc_to_dict(doc)
    await _audit(db, org_id, user, "VISA_CREATED", result["id"], {"customer_name": body.customer_name, "country": body.destination_country})
    return result


@router.patch("/{visa_id}", dependencies=[AdminDep])
async def patch_visa_application(visa_id: str, body: VisaApplicationPatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise AppError(400, "NO_CHANGES", "Guncelleme verisi yok")

    if "status" in updates and updates["status"] not in VISA_STATUSES:
        raise AppError(400, "INVALID", f"Gecersiz durum. Gecerli degerler: {', '.join(VISA_STATUSES)}")

    now = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now

    timeline_entry = None
    if "status" in updates:
        timeline_entry = {"date": now, "action": f"status_changed_to_{updates['status']}", "note": ""}

    update_ops: Dict[str, Any] = {"$set": updates}
    if timeline_entry:
        update_ops["$push"] = {"timeline": timeline_entry}

    result = await db.visa_applications.update_one(
        {"id": visa_id, "organization_id": org_id}, update_ops
    )
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Vize basvurusu bulunamadi")
    doc = await db.visa_applications.find_one({"id": visa_id, "organization_id": org_id}, {"_id": 0})
    await _audit(db, org_id, user, "VISA_UPDATED", visa_id, {"fields": list(updates.keys())})
    return _doc_to_dict(doc)


@router.delete("/{visa_id}", dependencies=[AdminDep])
async def delete_visa_application(visa_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.visa_applications.delete_one({"id": visa_id, "organization_id": org_id})
    if result.deleted_count == 0:
        raise AppError(404, "NOT_FOUND", "Vize basvurusu bulunamadi")
    await _audit(db, org_id, user, "VISA_DELETED", visa_id)
    return {"ok": True}


@router.post("/{visa_id}/timeline", dependencies=[AdminDep])
async def add_timeline_entry(visa_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "date": now,
        "action": payload.get("action", "note"),
        "note": payload.get("note", ""),
        "by": user.get("email"),
    }
    result = await db.visa_applications.update_one(
        {"id": visa_id, "organization_id": org_id},
        {"$push": {"timeline": entry}, "$set": {"updated_at": now}},
    )
    if result.matched_count == 0:
        raise AppError(404, "NOT_FOUND", "Vize basvurusu bulunamadi")
    return {"ok": True}


@router.post("/bulk-status", dependencies=[AdminDep])
async def bulk_update_status(payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    ids = payload.get("ids", [])
    new_status = payload.get("status", "")
    if not ids or not new_status:
        raise AppError(400, "INVALID", "ids ve status alanlari gereklidir")
    if new_status not in VISA_STATUSES:
        raise AppError(400, "INVALID", f"Gecersiz durum. Gecerli degerler: {', '.join(VISA_STATUSES)}")
    now = datetime.now(timezone.utc).isoformat()
    result = await db.visa_applications.update_many(
        {"id": {"$in": ids}, "organization_id": org_id},
        {
            "$set": {"status": new_status, "updated_at": now},
            "$push": {"timeline": {"date": now, "action": f"bulk_status_to_{new_status}", "note": "Toplu guncelleme"}},
        },
    )
    await _audit(db, org_id, user, "VISA_BULK_STATUS", ",".join(ids[:5]), {"status": new_status, "count": result.modified_count})
    return {"ok": True, "modified_count": result.modified_count}
