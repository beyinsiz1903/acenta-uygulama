"""Finance Documents Router — Decomposed from ops_finance.py.

Handles: document upload, list, download, delete for refund case evidence.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional, Any

from fastapi import APIRouter, Depends, Query, Request, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from bson import ObjectId

from app.db import get_db
from app.auth import require_roles
from app.errors import AppError
from app.utils import now_utc
from app.services.audit import write_audit_log
from app.services.booking_events import emit_event
from app.services.refund_cases import RefundCaseService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ops/finance", tags=["ops_finance_documents"])


def _get_upload_dir() -> str:
    base = os.environ.get("UPLOAD_DIR") or "./uploads"
    return os.path.join(base, "refunds")


def _actor(user):
    return {
        "actor_type": "user",
        "actor_id": user.get("id") or user.get("email"),
        "email": user.get("email"),
        "roles": user.get("roles") or [],
    }


@router.post("/documents/upload")
async def upload_document(
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    tag: str = Form(...),
    note: Optional[str] = Form(None),
    file: UploadFile = File(...),
    request: Request = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    if entity_type != "refund_case":
        raise AppError(400, "unsupported_entity_type", "Only refund_case is supported")
    svc = RefundCaseService(db)
    case = await svc.get_case(org_id, entity_id)
    if not case:
        raise AppError(404, "refund_case_not_found", "Refund case not found")
    booking_id = case.get("booking_id")
    allowed_tags = {"refund_proof", "invoice", "correspondence", "other"}
    if tag not in allowed_tags:
        tag = "other"
    now = now_utc()
    original_filename = file.filename or "upload.bin"
    safe_name = original_filename.replace("/", "_").replace("\\", "_")
    doc = {
        "organization_id": org_id, "created_at": now,
        "created_by_email": current_user.get("email"),
        "created_by_actor_id": current_user.get("id"),
        "filename": safe_name,
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": 0, "storage": {"provider": "local", "path": None},
        "sha256": None, "status": "active",
    }
    res = await db.documents.insert_one(doc)
    doc_id = res.inserted_id
    base_dir = _get_upload_dir()
    case_dir = os.path.join(base_dir, entity_id)
    os.makedirs(case_dir, exist_ok=True)
    disk_path = os.path.join(case_dir, f"{doc_id}_{safe_name}")
    sha256 = hashlib.sha256()
    size = 0
    with open(disk_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            sha256.update(chunk)
            size += len(chunk)
    await db.documents.update_one(
        {"_id": doc_id},
        {"$set": {"size_bytes": size, "storage.path": disk_path, "sha256": sha256.hexdigest()}},
    )
    link = {"organization_id": org_id, "created_at": now, "entity_type": entity_type, "entity_id": entity_id, "document_id": doc_id, "tag": tag, "note": note}
    link_res = await db.document_links.insert_one(link)
    try:
        await write_audit_log(db, organization_id=org_id, actor=_actor(current_user), request=request, action="document_upload", target_type="document", target_id=str(doc_id), before=None, after={"document_id": str(doc_id), "filename": safe_name, "tag": tag, "entity_type": entity_type, "entity_id": entity_id}, meta={"entity_type": entity_type, "entity_id": entity_id, "tag": tag, "filename": safe_name, "size_bytes": size, "content_type": file.content_type})
    except Exception:
        logger.exception("audit_write_failed action=document_upload")
    if booking_id:
        try:
            await emit_event(db, organization_id=org_id, booking_id=booking_id, type="DOCUMENT_UPLOADED", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"entity_type": entity_type, "entity_id": entity_id, "document_id": str(doc_id), "tag": tag, "filename": safe_name})
        except Exception:
            logger.exception("event_emit_failed type=DOCUMENT_UPLOADED")
    return {"document_id": str(doc_id), "link_id": str(link_res.inserted_id), "filename": safe_name, "tag": tag, "size_bytes": size, "content_type": file.content_type, "created_at": now, "created_by_email": current_user.get("email"), "status": "active"}


@router.get("/documents")
async def list_documents(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    include_deleted: bool = Query(False),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    if entity_type != "refund_case":
        raise AppError(400, "unsupported_entity_type", "Only refund_case is supported")
    links = await db.document_links.find({"organization_id": org_id, "entity_type": entity_type, "entity_id": entity_id}).to_list(length=500)
    if not links:
        return {"entity_type": entity_type, "entity_id": entity_id, "items": []}
    doc_ids = [link["document_id"] for link in links]
    doc_query: dict[str, Any] = {"_id": {"$in": doc_ids}, "organization_id": org_id}
    if not include_deleted:
        doc_query["status"] = {"$ne": "deleted"}
    docs = await db.documents.find(doc_query).to_list(length=len(doc_ids))
    docs_by_id = {d["_id"]: d for d in docs}
    items = []
    for link in links:
        d = docs_by_id.get(link["document_id"])
        if not d:
            continue
        items.append({"document_id": str(d["_id"]), "link_id": str(link["_id"]), "tag": link.get("tag"), "note": link.get("note"), "filename": d.get("filename"), "content_type": d.get("content_type"), "size_bytes": d.get("size_bytes"), "created_at": d.get("created_at"), "created_by_email": d.get("created_by_email"), "status": d.get("status", "active")})
    return {"entity_type": entity_type, "entity_id": entity_id, "items": items}


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    try:
        oid = ObjectId(document_id)
    except Exception:
        raise AppError(404, "document_not_found", "Document not found")
    doc = await db.documents.find_one({"_id": oid, "organization_id": org_id})
    if not doc or doc.get("status") == "deleted":
        raise AppError(404, "document_not_found", "Document not found")
    storage = doc.get("storage") or {}
    path = storage.get("path")
    if not path or not os.path.exists(path):
        raise AppError(404, "file_not_found", "File content not found")
    filename = doc.get("filename") or "file.bin"
    content_type = doc.get("content_type") or "application/octet-stream"

    def iterfile():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
    return StreamingResponse(iterfile(), media_type=content_type, headers=headers)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str, payload: Optional[dict] = None, request: Request = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    reason = (payload or {}).get("reason") if isinstance(payload, dict) else None
    try:
        oid = ObjectId(document_id)
    except Exception:
        raise AppError(404, "document_not_found", "Document not found")
    doc = await db.documents.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise AppError(404, "document_not_found", "Document not found")
    already_deleted = doc.get("status") == "deleted"
    if not already_deleted:
        await db.documents.update_one({"_id": oid}, {"$set": {"status": "deleted"}})
    links = await db.document_links.find({"organization_id": org_id, "document_id": oid}).to_list(length=100)
    entity_type = links[0].get("entity_type") if links else None
    entity_id = links[0].get("entity_id") if links else None
    tag = links[0].get("tag") if links else None
    try:
        await write_audit_log(db, organization_id=org_id, actor=_actor(current_user), request=request, action="document_delete", target_type="document", target_id=document_id, before={"document_id": document_id, "filename": doc.get("filename"), "tag": tag}, after={"document_id": document_id, "status": "deleted"}, meta={"reason": reason, "entity_type": entity_type, "entity_id": entity_id})
    except Exception:
        logger.exception("audit_write_failed action=document_delete")
    if not already_deleted and entity_type == "refund_case" and entity_id:
        svc = RefundCaseService(db)
        case = await svc.get_case(org_id, entity_id)
        booking_id = case.get("booking_id") if case else None
        if booking_id:
            try:
                await emit_event(db, organization_id=org_id, booking_id=booking_id, type="DOCUMENT_DELETED", actor={"email": current_user.get("email"), "actor_id": current_user.get("id"), "roles": current_user.get("roles") or []}, meta={"entity_type": entity_type, "entity_id": entity_id, "document_id": document_id, "filename": doc.get("filename"), "tag": tag, "reason": reason})
            except Exception:
                logger.exception("event_emit_failed type=DOCUMENT_DELETED")
    return {"ok": True}
