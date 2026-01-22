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

    # Optional org scoping for multi-tenant safety.
    org_id = request.query_params.get("org")

    # Use a dict keyed by loc to avoid duplicates when combining hotels/products
    url_map: dict[str, dict[str, str]] = {}

    # Static important URLs – PUBLIC surfaces only
    static_paths = [
        "/",       # home / landing (şu an login olsa da ileride marketing yüzeyi olacak)
        "/book",   # public arama/listleme yüzeyi
    ]
    today = datetime.utcnow().date().isoformat()
    for path in static_paths:
        url_map[f"{base_url}{path}"] = {
            "loc": f"{base_url}{path}",
            "lastmod": today,
            "priority": "1.0" if path == "/" else "0.8",
        }

    # Dynamic hotel detail URLs from legacy hotels collection (if exists)
    try:
        hotels = await db.hotels.find({"active": True}, {"_id": 1, "updated_at": 1, "created_at": 1}).to_list(500)
    except Exception:
        hotels = []

    for h in hotels:
        hid = str(h.get("_id"))
        lastmod = _format_date(h.get("updated_at")) or _format_date(h.get("created_at")) or today
        loc = f"{base_url}/book/{hid}"  # canonical pattern: /book/{productId}
        url_map[loc] = {"loc": loc, "lastmod": lastmod, "priority": "0.6"}

    # Dynamic hotel URLs from products collection (fallback / new source).
    # Multi-tenant güvenliği için org param'ı yoksa products üzerinden URL üretmeyiz.
    if org_id:
        try:
            products = await db.products.find(
                {"type": "hotel", "status": "active", "organization_id": org_id},
                {"_id": 1, "updated_at": 1, "created_at": 1},
            ).to_list(1000)
        except Exception:
            products = []

        for p in products:
            pid = str(p.get("_id"))
            lastmod = _format_date(p.get("updated_at")) or _format_date(p.get("created_at")) or today
            loc = f"{base_url}/book/{pid}"  # canonical pattern: /book/{productId}
            # Do not downgrade existing lastmod/priority if already present
            if loc not in url_map:
                url_map[loc] = {"loc": loc, "lastmod": lastmod, "priority": "0.6"}

        # Dynamic campaign URLs for this tenant
        try:
            campaigns = await db.campaigns.find(
                {"organization_id": org_id, "active": True},
                {"slug": 1, "updated_at": 1, "created_at": 1},
            ).to_list(500)
        except Exception:
            campaigns = []

        for c in campaigns:
            slug = c.get("slug") or ""
            if not slug:
                continue
            lastmod = _format_date(c.get("updated_at")) or _format_date(c.get("created_at")) or today
            loc = f"{base_url}/campaigns/{slug}"
            if loc not in url_map:
                url_map[loc] = {"loc": loc, "lastmod": lastmod, "priority": "0.5"}

    urls: List[dict[str, str]] = list(url_map.values())

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



from app.auth import require_feature, require_super_admin_only


SeoAdminDep = Depends(require_super_admin_only())
SeoFeatureDep = Depends(require_feature("seo_plus"))


@router.post("/admin/seo/indexnow/reindex", include_in_schema=False)
async def admin_indexnow_reindex(
    request: Request,
    db=Depends(get_db),
    user=SeoAdminDep,  # noqa: B008
    _feature=SeoFeatureDep,  # noqa: B008
) -> dict[str, Any]:
    """Admin-only helper to enqueue IndexNow submissions for key public URLs.

    Behaviour:
    - Always returns 200 with a simple summary payload.
    - If IndexNow is disabled or not configured, we still return ok=true but
      note that submissions were skipped; the underlying job handler will mark
      jobs as succeeded-with-skipped semantics.
    - We do not implement auth/role checks here because this router already
      lives behind /app admin UI; actual protection is managed by upstream
      routing/auth layer.
    """

    base_url = str(request.base_url).rstrip("/")

    # Static important URLs for this tenant
    urls: list[str] = [
        f"{base_url}/",
        f"{base_url}/book",
    ]

    # In a multi-tenant scenario we could scope by organization; for now, we
    # reuse the "default" organization for IndexNow jobs.
    org_doc = await db.organizations.find_one({"slug": "default"}, {"_id": 1})
    if not org_doc:
        return {"ok": False, "reason": "default_org_missing", "enqueued_jobs": 0}

    org_id = str(org_doc["_id"])

    from app.services.jobs import enqueue_indexnow_job

    job = await enqueue_indexnow_job(db, organization_id=org_id, urls=urls)

    return {"ok": True, "enqueued_jobs": 1, "job_id": str(job.get("_id"))}
