from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.db import get_db

router = APIRouter(prefix="/api/public/cms/pages", tags=["public_cms_pages"])


@router.get("/{slug}")
async def get_cms_page(slug: str, org: str = Query(..., min_length=1), db=Depends(get_db)) -> JSONResponse:
    doc = await db.cms_pages.find_one({"organization_id": org, "slug": slug, "published": True})
    if not doc:
        return JSONResponse(status_code=404, content={"code": "PAGE_NOT_FOUND", "message": "Sayfa bulunamadı"})

    payload: Dict[str, Any] = {
        "id": str(doc.get("_id")),
        "slug": doc.get("slug") or "",
        "title": doc.get("title") or "",
        "body": doc.get("body") or "",
        "seo_title": doc.get("seo_title") or "",
        "seo_description": doc.get("seo_description") or "",
    }
    return JSONResponse(status_code=200, content=payload)
