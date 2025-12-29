from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db
from app.auth import require_roles, get_current_user

router = APIRouter(prefix="/api/agency", tags=["agency:tours"])


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _serialize_tour(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d["_id"])
        d.pop("_id", None)
    return d


def _normalize_images(images: Any) -> List[str]:
    if not images:
        return []
    if isinstance(images, list):
        return [str(x).strip() for x in images if str(x).strip()]
    if isinstance(images, str):
        return [x.strip() for x in images.splitlines() if x.strip()]
    return []


@router.get("/tours")
async def agency_list_tours(
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    agency_id = str(user.get("agency_id"))
    cursor = db.tours.find(
        {"agency_id": agency_id},
        sort=[("created_at", -1)],
        projection={
            "_id": 1,
            "organization_id": 1,
            "title": 1,
            "description": 1,
            "price": 1,
            "currency": 1,
            "images": 1,
            "status": 1,
            "created_at": 1,
            "updated_at": 1,
        },
    )
    return [_serialize_tour(x) async for x in cursor]


@router.post("/tours")
async def agency_create_tour(
    payload: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    org_id = user["organization_id"]
    agency_id = str(user.get("agency_id"))
    now = _now_iso()

    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="TITLE_REQUIRED")

    doc = {
        "_id": payload.get("id") or payload.get("_id") or f"TOUR_{int(datetime.utcnow().timestamp())}",
        "organization_id": str(org_id),
        "agency_id": agency_id,
        "title": title,
        "description": (payload.get("description") or "").strip(),
        "price": float(payload.get("price") or 0),
        "currency": (payload.get("currency") or "TRY").strip() or "TRY",
        "images": _normalize_images(payload.get("images")),
        "status": (payload.get("status") or "draft").strip(),
        "created_at": now,
        "updated_at": now,
        "created_by": {
            "user_id": user.get("user_id") or user.get("id"),
            "email": user.get("email"),
            "role": user.get("role"),
        },
    }

    if doc["status"] not in ["active", "draft"]:
        doc["status"] = "draft"

    existing = await db.tours.find_one({"_id": doc["_id"], "agency_id": agency_id})
    if existing:
        raise HTTPException(status_code=409, detail="TOUR_ALREADY_EXISTS")

    await db.tours.insert_one(doc)
    return _serialize_tour(doc)


@router.put("/tours/{tour_id}")
async def agency_update_tour(
    tour_id: str,
    payload: Dict[str, Any],
    db=Depends(get_db),
    user: Dict[str, Any] = Depends(require_roles(["agency_admin", "agency_agent"])),
):
    org_id = user["organization_id"]
    agency_id = str(user.get("agency_id"))
    now = _now_iso()

    existing = await db.tours.find_one({"_id": tour_id, "agency_id": agency_id})
    if not existing:
        raise HTTPException(status_code=404, detail="TOUR_NOT_FOUND")

    updates: Dict[str, Any] = {"updated_at": now}

    if "title" in payload:
        t = (payload.get("title") or "").strip()
        if not t:
            raise HTTPException(status_code=400, detail="TITLE_REQUIRED")
        updates["title"] = t

    if "description" in payload:
        updates["description"] = (payload.get("description") or "").strip()

    if "price" in payload:
        updates["price"] = float(payload.get("price") or 0)

    if "currency" in payload:
        updates["currency"] = (payload.get("currency") or "TRY").strip() or "TRY"

    if "images" in payload:
        updates["images"] = _normalize_images(payload.get("images"))

    if "status" in payload:
        s = (payload.get("status") or "draft").strip()
        updates["status"] = s if s in ["active", "draft"] else "draft"

    await db.tours.update_one({"_id": tour_id, "agency_id": agency_id}, {"$set": updates})
    doc = await db.tours.find_one({"_id": tour_id, "agency_id": agency_id})
    return _serialize_tour(doc)
