from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db

router = APIRouter(prefix="/api/admin/b2b/announcements", tags=["admin_b2b_announcements"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


def _now_utc() -> datetime:
  return datetime.now(timezone.utc)


@router.get("", dependencies=[AdminDep])
async def list_announcements(user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    """List B2B announcements for current org (admin view).

    Simple read-only listing; filtered by organization_id.
    """

    org_id = user["organization_id"]
    cursor = (
        db.b2b_announcements.find({"organization_id": org_id})
        .sort("created_at", -1)
        .limit(200)
    )
    docs = await cursor.to_list(length=200)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        _id = str(doc.get("_id"))
        items.append(
            {
                "id": _id,
                "title": doc.get("title") or "",
                "body": doc.get("body") or "",
                "audience": doc.get("audience") or "all",
                "agency_id": doc.get("agency_id"),
                "is_active": bool(doc.get("is_active", True)),
                "valid_from": (doc.get("valid_from") or ""),
                "valid_until": (doc.get("valid_until") or ""),
                "created_at": (doc.get("created_at") or ""),
                "created_by": doc.get("created_by"),
            }
        )

    return {"items": items}


@router.post("", dependencies=[AdminDep])
async def create_announcement(payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    """Create a simple B2B announcement.

    Expected payload fields (all optional except title/body):
    - title: str
    - body: str
    - audience: "all" | "agency" (default: "all")
    - agency_id: str (required if audience=="agency")
    - is_active: bool (default: True)
    - days_valid: int (optional, used to set valid_until from now)
    """

    org_id = user["organization_id"]
    now = _now_utc().isoformat()

    title = (payload.get("title") or "").strip()
    body = (payload.get("body") or "").strip()
    audience = (payload.get("audience") or "all").strip() or "all"
    agency_id: Optional[str] = (payload.get("agency_id") or None)
    is_active = bool(payload.get("is_active", True))

    if not title or not body:
        from app.errors import AppError

        raise AppError(400, "invalid_payload", "title ve body alanları zorunludur")

    if audience not in {"all", "agency"}:
        audience = "all"

    if audience == "agency" and not agency_id:
        from app.errors import AppError

        raise AppError(400, "invalid_payload", "audience='agency' için agency_id zorunludur")

    valid_from = now
    valid_until = None
    days_valid = payload.get("days_valid")
    if isinstance(days_valid, int) and days_valid > 0:
        valid_until_dt = _now_utc() + timedelta(days=days_valid)
        valid_until = valid_until_dt.isoformat()

    doc = {
        "organization_id": org_id,
        "title": title,
        "body": body,
        "audience": audience,
        "agency_id": agency_id,
        "is_active": is_active,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "created_at": now,
        "created_by": user.get("email") or user.get("id"),
    }

    res = await db.b2b_announcements.insert_one(doc)
    _id = str(res.inserted_id)

    return {
        "id": _id,
        "title": title,
        "body": body,
        "audience": audience,
        "agency_id": agency_id,
        "is_active": is_active,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "created_at": now,
        "created_by": doc["created_by"],
    }


@router.post("/{announcement_id}/toggle", dependencies=[AdminDep])
async def toggle_active(announcement_id: str, user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    """Toggle is_active flag for an announcement.

    Simple activation/deactivation helper; stays in same org scope.
    """

    org_id = user["organization_id"]
    existing = await db.b2b_announcements.find_one(
        {"_id": announcement_id, "organization_id": org_id}
    )
    if not existing:
        from app.errors import AppError

        raise AppError(404, "not_found", "Duyuru bulunamadı")

    current = bool(existing.get("is_active", True))
    new_val = not current

    await db.b2b_announcements.update_one(
        {"_id": existing["_id"]}, {"$set": {"is_active": new_val}}
    )

    return {"id": str(existing["_id"]), "is_active": new_val}
