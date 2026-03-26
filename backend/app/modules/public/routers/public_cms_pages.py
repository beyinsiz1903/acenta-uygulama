from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.db import get_db
from app.services.endpoint_cache import try_cache_get, cache_and_return

router = APIRouter(prefix="/api/public/cms/pages", tags=["public_cms_pages"])


@router.get("/{slug}")
async def get_cms_page(slug: str, org: str = Query(..., min_length=1), db=Depends(get_db)) -> JSONResponse:
    # Redis L1 cache (10 min — CMS content changes rarely)
    hit, ck = await try_cache_get("cms_page", org, {"slug": slug})
    if hit:
        resp = JSONResponse(status_code=200, content=hit)
        resp.headers["X-Cache"] = "HIT"
        return resp

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
        "kind": doc.get("kind") or "page",
        "linked_campaign_slug": doc.get("linked_campaign_slug") or "",
    }
    await cache_and_return(ck, payload, ttl=600)
    return JSONResponse(status_code=200, content=payload)


@router.get("", summary="List published CMS pages for navigation")
async def list_cms_pages_for_nav(org: str = Query(..., min_length=1), db=Depends(get_db)) -> JSONResponse:
    """Return a simple list of published CMS pages for navigation menus."""

    # Redis L1 cache (10 min)
    hit, ck = await try_cache_get("cms_nav", org)
    if hit:
        resp = JSONResponse(status_code=200, content=hit)
        resp.headers["X-Cache"] = "HIT"
        return resp

    cursor = db.cms_pages.find({"organization_id": org, "published": True}, {"_id": 1, "slug": 1, "title": 1}).sort(
        "created_at", -1
    )
    docs = await cursor.to_list(length=200)

    items = [
        {"id": str(doc.get("_id")), "slug": doc.get("slug") or "", "title": doc.get("title") or ""}
        for doc in docs
    ]
    result = {"items": items}
    await cache_and_return(ck, result, ttl=600)
    return JSONResponse(status_code=200, content=result)

