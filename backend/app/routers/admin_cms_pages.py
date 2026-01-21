from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/cms/pages", tags=["admin_cms_pages"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))


@router.get("", dependencies=[AdminDep])
async def list_cms_pages(user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user["organization_id"]
    cursor = (
        db.cms_pages.find({"organization_id": org_id})
        .sort("created_at", -1)
        .limit(200)
    )
    docs = await cursor.to_list(length=200)
    items: List[Dict[str, Any]] = []
    for doc in docs:
        items.append(
            {
                "id": str(doc.get("_id")),
                "slug": doc.get("slug") or "",
                "title": doc.get("title") or "",
                "published": bool(doc.get("published", True)),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
            }
        )
    return {"items": items}


@router.post("", dependencies=[AdminDep])
async def create_cms_page(payload: Dict[str, Any], user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user["organization_id"]
    now = datetime.now(timezone.utc).isoformat()

    slug = (payload.get("slug") or "").strip()
    title = (payload.get("title") or "").strip()
    body = payload.get("body") or ""
    seo_title = (payload.get("seo_title") or title).strip()
    seo_description = (payload.get("seo_description") or "").strip()
    published = bool(payload.get("published", True))

    if not slug or not title:
        from app.errors import AppError

        raise AppError(400, "invalid_payload", "slug ve title alanları zorunludur")

    doc: Dict[str, Any] = {
        "organization_id": org_id,
        "slug": slug,
        "title": title,
        "body": body,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "published": published,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.cms_pages.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_doc(doc)
