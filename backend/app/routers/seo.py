from __future__ import annotations

from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.db import get_db

router = APIRouter(prefix="/api", tags=["seo"])


def _format_date(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.date().isoformat()
    try:
        # string or date-like
        return str(dt)[:10]
    except Exception:
        return ""


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml(request: Request, db=Depends(get_db)) -> Response:
    """Minimal sitemap.xml for SEO base v0.

    - Includes a few static operational URLs
    - Adds hotel detail URLs for active hotels (if any)
    """

    base_url = str(request.base_url).rstrip("/")

    urls: List[dict[str, str]] = []

    # Static important URLs – PUBLIC surfaces only
    static_paths = [
        "/",       # home / landing (şu an login olsa da ileride marketing yüzeyi olacak)
        "/book",   # public arama/listleme yüzeyi
    ]
    today = datetime.utcnow().date().isoformat()
    for path in static_paths:
        urls.append({"loc": f"{base_url}{path}", "lastmod": today})

    # Dynamic hotel detail URLs (if hotels collection exists & has active docs)
    try:
        hotels = await db.hotels.find({"active": True}, {"_id": 1, "updated_at": 1}).to_list(500)
    except Exception:
        hotels = []

    for h in hotels:
        hid = str(h.get("_id"))
        lastmod = _format_date(h.get("updated_at")) or today
        # Using agency hotel detail route as canonical detail surface
        loc = f"{base_url}/app/agency/hotels/{hid}"
        urls.append({"loc": loc, "lastmod": lastmod})

    # Build XML
    items: List[str] = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
    ]
    for u in urls:
        items.append("  <url>")
        items.append(f"    <loc>{u['loc']}</loc>")
        if u.get("lastmod"):
            items.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        items.append("  </url>")
    items.append("</urlset>")

    xml = "\n".join(items)
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt(request: Request) -> Response:
    """Basic robots.txt pointing to sitemap.

    Served under /api/robots.txt; in real deployment this can be mirrored at root.
    """

    base_url = str(request.base_url).rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {base_url}/api/sitemap.xml",
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain")
