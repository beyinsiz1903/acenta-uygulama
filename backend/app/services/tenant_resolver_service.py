from __future__ import annotations

from app.db import get_db
from app.errors import AppError
from app.services.redis_cache import redis_get, redis_set


TENANT_LOOKUP_CACHE_PREFIX = "tenant_lookup"
TENANT_LOOKUP_TTL_SECONDS = 600


async def resolve_tenant_id_for_org(organization_id: str) -> str:
    org_id = str(organization_id or "").strip()
    if not org_id:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {"reason": "organization_missing"})

    cache_key = f"{TENANT_LOOKUP_CACHE_PREFIX}:{org_id}"
    cached = await redis_get(cache_key)
    if cached:
        return str(cached)

    db = await get_db()
    tenant = await db.tenants.find_one({"organization_id": org_id}, {"_id": 1}, sort=[("created_at", 1)])
    if not tenant or tenant.get("_id") is None:
        raise AppError(404, "tenant_not_found", "Tenant bulunamadı.", {"organization_id": org_id})

    tenant_id = str(tenant.get("_id"))
    await redis_set(cache_key, tenant_id, ttl_seconds=TENANT_LOOKUP_TTL_SECONDS)
    return tenant_id