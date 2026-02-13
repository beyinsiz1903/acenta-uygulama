from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/tours", tags=["admin_tours"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "tours")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _tour_to_dict(doc: dict) -> dict:
    """Convert a MongoDB tour document to a serializable dict."""
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name") or "",
        "description": doc.get("description") or "",
        "destination": doc.get("destination") or "",
        "departure_city": doc.get("departure_city") or "",
        "category": doc.get("category") or "",
        "base_price": float(doc.get("base_price") or 0.0),
        "currency": (doc.get("currency") or "EUR").upper(),
        "status": doc.get("status") or "active",
        "duration_days": int(doc.get("duration_days") or 1),
        "max_participants": int(doc.get("max_participants") or 0),
        "cover_image": doc.get("cover_image") or "",
        "images": doc.get("images") or [],
        "itinerary": doc.get("itinerary") or [],
        "includes": doc.get("includes") or [],
        "excludes": doc.get("excludes") or [],
        "highlights": doc.get("highlights") or [],
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


@router.get("", dependencies=[AdminDep])
async def list_tours(user=Depends(get_current_user), db=Depends(get_db)) -> List[Dict[str, Any]]:
    org_id = user["organization_id"]
    cursor = db.tours.find({"organization_id": org_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [_tour_to_dict(doc) for doc in docs]


@router.get("/{tour_id}", dependencies=[AdminDep])
async def get_tour(tour_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    from bson import ObjectId
    from bson.errors import InvalidId

    org_id = user["organization_id"]
    try:
        oid = ObjectId(tour_id)
    except (InvalidId, Exception):
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    doc = await db.tours.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    return _tour_to_dict(doc)


@router.post("", dependencies=[AdminDep])
async def create_tour(payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()

    name = (payload.get("name") or "").strip()
    if not name:
        from app.errors import AppError
        raise AppError(400, "invalid_payload", "Tur adi zorunludur")

    destination = (payload.get("destination") or "").strip()
    departure_city = (payload.get("departure_city") or "").strip()
    category = (payload.get("category") or "").strip()
    description = (payload.get("description") or "").strip()
    base_price = float(payload.get("base_price") or 0.0)
    currency = (payload.get("currency") or "EUR").upper()
    status = (payload.get("status") or "active").strip() or "active"
    duration_days = int(payload.get("duration_days") or 1)
    max_participants = int(payload.get("max_participants") or 0)
    cover_image = (payload.get("cover_image") or "").strip()
    images = payload.get("images") or []
    itinerary = payload.get("itinerary") or []
    includes = payload.get("includes") or []
    excludes = payload.get("excludes") or []
    highlights = payload.get("highlights") or []

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "type": "tour",
        "name": name,
        "name_search": name.lower(),
        "description": description,
        "destination": destination,
        "departure_city": departure_city,
        "category": category,
        "base_price": base_price,
        "currency": currency,
        "status": status,
        "duration_days": duration_days,
        "max_participants": max_participants,
        "cover_image": cover_image,
        "images": images,
        "itinerary": itinerary,
        "includes": includes,
        "excludes": excludes,
        "highlights": highlights,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.tours.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _tour_to_dict(doc)


@router.put("/{tour_id}", dependencies=[AdminDep])
async def update_tour(tour_id: str, payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)):
    from bson import ObjectId
    from bson.errors import InvalidId

    org_id = user["organization_id"]
    try:
        oid = ObjectId(tour_id)
    except (InvalidId, Exception):
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    doc = await db.tours.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    now = datetime.now(timezone.utc).isoformat()

    update_fields: Dict[str, Any] = {"updated_at": now}

    allowed = [
        "name", "description", "destination", "departure_city", "category",
        "base_price", "currency", "status", "duration_days", "max_participants",
        "cover_image", "images", "itinerary", "includes", "excludes", "highlights",
    ]

    for key in allowed:
        if key in payload:
            val = payload[key]
            if key == "name":
                val = (val or "").strip()
                if not val:
                    continue
                update_fields["name_search"] = val.lower()
            if key == "base_price":
                val = float(val or 0.0)
            if key == "currency":
                val = (val or "EUR").upper()
            if key in ("duration_days", "max_participants"):
                val = int(val or 0)
            update_fields[key] = val

    await db.tours.update_one({"_id": oid}, {"$set": update_fields})

    updated = await db.tours.find_one({"_id": oid})
    return _tour_to_dict(updated)


@router.delete("/{tour_id}", dependencies=[AdminDep])
async def delete_tour(tour_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    from bson import ObjectId
    from bson.errors import InvalidId

    org_id = user["organization_id"]
    try:
        oid = ObjectId(tour_id)
    except (InvalidId, Exception):
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    result = await db.tours.delete_one({"_id": oid, "organization_id": org_id})
    if result.deleted_count == 0:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Tur bulunamadi"})

    return {"ok": True, "message": "Tur silindi"}


@router.post("/upload-image", dependencies=[AdminDep])
async def upload_tour_image(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload a tour image and return the URL."""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse(status_code=400, content={"code": "INVALID_FILE", "message": "Sadece resim dosyalari yuklenebilir"})

    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    allowed_ext = {"jpg", "jpeg", "png", "webp", "gif"}
    if ext.lower() not in allowed_ext:
        ext = "jpg"

    filename = f"{uuid.uuid4().hex}.{ext.lower()}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        return JSONResponse(status_code=400, content={"code": "FILE_TOO_LARGE", "message": "Dosya boyutu 10MB'dan buyuk olamaz"})

    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/api/uploads/tours/{filename}"
    return {"ok": True, "url": url, "filename": filename}
