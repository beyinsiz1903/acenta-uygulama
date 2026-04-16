from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/admin/email-templates", tags=["admin-email-templates"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))

TEMPLATE_TRIGGERS = [
    "reservation.confirmed",
    "reservation.cancelled",
    "reservation.reminder",
    "reservation.checkin_reminder",
    "payment.received",
    "payment.reminder",
    "quote.sent",
    "quote.expired",
    "visa.status_changed",
    "visa.appointment_reminder",
    "insurance.policy_created",
    "transfer.confirmed",
    "welcome",
    "password_reset",
]

DEFAULT_TEMPLATES = [
    {
        "key": "reservation_confirmed",
        "name": "Rezervasyon Onay",
        "trigger": "reservation.confirmed",
        "subject": "Rezervasyonunuz Onaylandi - {{reservation_code}}",
        "body_html": "<h2>Sayin {{customer_name}},</h2><p>{{reservation_code}} kodlu rezervasyonunuz onaylanmistir.</p><p>Giris: {{check_in}}<br/>Cikis: {{check_out}}</p>",
        "language": "tr",
    },
    {
        "key": "reservation_cancelled",
        "name": "Rezervasyon Iptal",
        "trigger": "reservation.cancelled",
        "subject": "Rezervasyonunuz Iptal Edildi - {{reservation_code}}",
        "body_html": "<h2>Sayin {{customer_name}},</h2><p>{{reservation_code}} kodlu rezervasyonunuz iptal edilmistir.</p>",
        "language": "tr",
    },
    {
        "key": "payment_reminder",
        "name": "Odeme Hatirlatma",
        "trigger": "payment.reminder",
        "subject": "Odeme Hatirlatmasi - {{reservation_code}}",
        "body_html": "<h2>Sayin {{customer_name}},</h2><p>{{amount}} {{currency}} tutarindaki odemenizi bekliyoruz.</p>",
        "language": "tr",
    },
    {
        "key": "quote_sent",
        "name": "Teklif Gonderimi",
        "trigger": "quote.sent",
        "subject": "Size Ozel Teklif - {{quote_code}}",
        "body_html": "<h2>Sayin {{customer_name}},</h2><p>Talebinize istinaden hazirladigimiz teklifi ekte bulabilirsiniz.</p>",
        "language": "tr",
    },
]


class EmailTemplateCreate(BaseModel):
    name: str
    key: str = ""
    trigger: str = ""
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    language: str = "tr"
    is_active: bool = True
    variables: List[str] = []
    notes: str = ""


class EmailTemplatePatch(BaseModel):
    name: Optional[str] = None
    trigger: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    variables: Optional[List[str]] = None
    notes: Optional[str] = None


def _doc_to_dict(doc: dict) -> dict:
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "name": doc.get("name", ""),
        "key": doc.get("key", ""),
        "trigger": doc.get("trigger", ""),
        "subject": doc.get("subject", ""),
        "body_html": doc.get("body_html", ""),
        "body_text": doc.get("body_text", ""),
        "language": doc.get("language", "tr"),
        "is_active": doc.get("is_active", True),
        "variables": doc.get("variables", []),
        "notes": doc.get("notes", ""),
        "organization_id": doc.get("organization_id"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


@router.get("", dependencies=[AdminDep])
async def list_templates(
    trigger: Optional[str] = None,
    language: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    filt: Dict[str, Any] = {"organization_id": org_id}
    if trigger:
        filt["trigger"] = trigger
    if language:
        filt["language"] = language
    if is_active is not None:
        filt["is_active"] = is_active
    total = await db.email_templates.count_documents(filt)
    skip = (page - 1) * page_size
    cursor = db.email_templates.find(filt, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    return {"items": [_doc_to_dict(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/triggers", dependencies=[AdminDep])
async def get_triggers():
    return {"triggers": TEMPLATE_TRIGGERS}


@router.get("/defaults", dependencies=[AdminDep])
async def get_default_templates():
    return {"templates": DEFAULT_TEMPLATES}


@router.post("/seed-defaults", dependencies=[AdminDep])
async def seed_default_templates(user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    for tpl in DEFAULT_TEMPLATES:
        exists = await db.email_templates.find_one(
            {"organization_id": org_id, "key": tpl["key"]}
        )
        if not exists:
            doc = {
                "id": str(uuid.uuid4()),
                "organization_id": org_id,
                **tpl,
                "body_text": "",
                "is_active": True,
                "variables": [],
                "notes": "",
                "created_at": now,
                "updated_at": now,
            }
            await db.email_templates.insert_one(doc)
            created += 1
    return {"ok": True, "created": created}


@router.get("/{template_id}", dependencies=[AdminDep])
async def get_template(template_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.email_templates.find_one({"id": template_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Sablon bulunamadi"})
    return _doc_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_template(body: EmailTemplateCreate, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()
    key = body.key or body.name.lower().replace(" ", "_").replace("-", "_")
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        **body.model_dump(),
        "key": key,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("id"),
    }
    await db.email_templates.insert_one(doc)
    return _doc_to_dict(doc)


@router.patch("/{template_id}", dependencies=[AdminDep])
async def patch_template(template_id: str, body: EmailTemplatePatch, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        return JSONResponse(status_code=400, content={"code": "NO_CHANGES", "message": "Guncelleme verisi yok"})
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.email_templates.update_one({"id": template_id, "organization_id": org_id}, {"$set": updates})
    if result.matched_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Sablon bulunamadi"})
    doc = await db.email_templates.find_one({"id": template_id, "organization_id": org_id}, {"_id": 0})
    return _doc_to_dict(doc)


@router.delete("/{template_id}", dependencies=[AdminDep])
async def delete_template(template_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    result = await db.email_templates.delete_one({"id": template_id, "organization_id": org_id})
    if result.deleted_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Sablon bulunamadi"})
    return {"ok": True}


@router.post("/{template_id}/preview", dependencies=[AdminDep])
async def preview_template(template_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    org_id = user["organization_id"]
    doc = await db.email_templates.find_one({"id": template_id, "organization_id": org_id}, {"_id": 0})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Sablon bulunamadi"})

    sample_data = payload.get("data", {})
    subject = doc.get("subject", "")
    body = doc.get("body_html", "")
    for key, value in sample_data.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value))
        body = body.replace(placeholder, str(value))

    return {"subject": subject, "body_html": body}
